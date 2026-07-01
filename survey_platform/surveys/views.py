# surveys/views.py
import json
import secrets
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from .models import (
    Survey,
    Response as Resp,
    Answer,
    Question,
    QuestionCondition,
    QuestionConditionGroup,
    Option,
    SurveyPage,
    AnalysisReport,
    AnalyticResults
)
from .serializers import (
    SurveyListSer, SurveyDetailSer, StartResponseSer, SubmitAnswerSer, AnalyticsSer, SurveyAnalyticsSer, ResponseReadSer,
    UserListSer, UserProfileSer, AdminUserUpdateSer, SurveyCreateUpdateSer, BulkQuestionsSer, BulkSurveyPagesSer,
    AdminSurveyListSer, AdminSurveyDetailSer, BulkQuestionConditionsSer, QuestionConditionReadSer, AnalysisReportCreateSer, 
    AnalysisReportListSer, AnalysisReportDetailSer, AnalyticResultsListSer, AnalyticResultsDetailSer,
    AnalyticsCsvExportSer, AnalyticsPdfExportSer, AnalyticsXlsxExportSer
)
from .permissions import IsAdminRole, IsOrganizerOrAdmin
from survey_analytics.analytics import question_distribution, survey_distribution
from .answer_services import (
    CHOICE_QTYPES,
    MATRIX_QTYPES,
    MULTI_CHOICE_QTYPES,
    add_matrix_cells,
    add_ranking_items,
    answer_has_value,
    validate_answer_payload,
)
from survey_analytics.advanced_analytics_serializers import (
    ChiSquareAnalysisSer,
    ClusterAnalysisSer,
    CorrespondenceAnalysisSer,
    CorrelationAnalysisSer,
    CrosstabAnalysisSer,
    FactorAnalysisSer,
    GroupComparisonSer,
    LogisticRegressionSer,
    MissingAnalysisSer,
    ReliabilityAnalysisSer,
    RegressionAnalysisSer,
    ScaleIndexSer,
    TimeAnalysisSer,
)
from survey_analytics.advanced_analytics_services import (
    run_chi_square_analysis,
    run_cluster_analysis,
    run_correspondence_analysis,
    run_correlation_analysis,
    run_crosstab_analysis,
    run_factor_analysis,
    run_group_comparison,
    run_logistic_regression_analysis,
    run_missing_analysis,
    run_reliability_analysis,
    run_regression_analysis,
    run_scale_index_analysis,
    run_time_analysis,
)
from survey_analytics.advanced_analytics_charts import build_report_section_chart
from .pdf_export import build_analytics_pdf
from .csv_export import build_analytics_csv
from .response_csv_export import build_responses_csv
from .xlsx_export import build_analytics_xlsx
from .branching_services import evaluate_conditions
from .survey_builder import create_question_items

User = get_user_model()

class SurveyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Survey.objects.all()
    def get_permissions(self):
        return [AllowAny()] if self.action in ["list", "retrieve", "start", "submit"] else [IsAuthenticated()]

    def get_serializer_class(self):
        return SurveyListSer if self.action == "list" else SurveyDetailSer

    def get_queryset(self):
        now = timezone.now()
        return Survey.objects.filter(
            status="active"
        ).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now)
        ).order_by("-created_at")

    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
    def start(self, request, pk=None):
        ser = StartResponseSer(data={"survey_id": pk})
        ser.is_valid(raise_exception=True)
        survey = self.get_object()
        token = secrets.token_urlsafe(24)
        resp = Resp.objects.create(survey=survey, session_token=token,
                                   user=request.user if request.user.is_authenticated and not survey.is_anonymous else None,
                                   client_meta={"ua": request.META.get("HTTP_USER_AGENT","")})
        return DRFResponse({"response_token": token}, status=201)

    @action(detail=False, methods=["post"], url_path="submit", permission_classes=[AllowAny])
    def submit(self, request):
        ser = SubmitAnswerSer(data=request.data); ser.is_valid(raise_exception=True)
        token = ser.validated_data["response_token"]
        answers = ser.validated_data["answers"]
        try:
            resp = Resp.objects.get(session_token=token, is_complete=False)
        except Resp.DoesNotExist:
            return DRFResponse({"detail":"invalid or completed token"}, status=400)

        if not resp.survey.is_anonymous and not request.user.is_authenticated:
            raise NotAuthenticated("Authentication credentials were not provided.")

        answer_question_ids = [a["question"] for a in answers]
        if len(answer_question_ids) != len(set(answer_question_ids)):
            return DRFResponse({"detail": "Duplicate answers for the same question are not allowed"}, status=400)

        questions = {
            question.id: question
            for question in Question.objects.filter(survey=resp.survey, id__in=answer_question_ids)
        }
        if len(questions) != len(set(answer_question_ids)):
            return DRFResponse({"detail": "question not in survey"}, status=400)

        answer_by_question = {a["question"]: a for a in answers}
        conditions = list(
            QuestionCondition.objects
            .filter(source_question__survey=resp.survey, is_active=True)
            .select_related("source_question", "question", "page", "target_page", "option", "matrix_row", "matrix_column", "group")
            .order_by("priority", "id")
        )
        questions_by_id = {
            question.id: question
            for question in Question.objects.filter(survey=resp.survey)
        }
        matched_conditions = evaluate_conditions(conditions, answer_by_question, questions_by_id)
        matched_condition_ids = {condition.id for condition in matched_conditions}
        terminate_conditions = [
            condition
            for condition in matched_conditions
            if condition.action == "terminate"
        ]

        page_show_conditions = [
            condition for condition in conditions if condition.action == "show_page" and condition.page_id
        ]
        question_show_conditions = [
            condition for condition in conditions if condition.action == "show_question" and condition.question_id
        ]
        hidden_page_ids = {
            condition.page_id
            for condition in page_show_conditions
            if not any(
                item.page_id == condition.page_id and item.id in matched_condition_ids
                for item in page_show_conditions
            )
        }
        hidden_question_ids = {
            condition.question_id
            for condition in question_show_conditions
            if not any(
                item.question_id == condition.question_id and item.id in matched_condition_ids
                for item in question_show_conditions
            )
        }

        required_questions = Question.objects.filter(survey=resp.survey, required=True)
        if not terminate_conditions:
            for question in required_questions:
                if question.id in hidden_question_ids or question.page_id in hidden_page_ids:
                    continue
                answer_data = answer_by_question.get(question.id)
                if not answer_data or not answer_has_value(question, answer_data):
                    return DRFResponse({"detail": f"Question {question.id} is required"}, status=400)

        for answer_data in answers:
            question = questions[answer_data["question"]]
            error = validate_answer_payload(question, answer_data)
            if error:
                return DRFResponse({"detail": error}, status=400)

            if question.qtype in CHOICE_QTYPES | MULTI_CHOICE_QTYPES and "selected_options" in answer_data:
                selected_options = answer_data.get("selected_options") or []
                valid_options_count = Option.objects.filter(
                    question=question,
                    id__in=selected_options,
                ).count()
                if valid_options_count != len(set(selected_options)):
                    return DRFResponse(
                        {"detail": f"Question {question.id} contains invalid selected options"},
                        status=400,
                    )

            if question.qtype == Question.RANKING and "ranking_items" in answer_data:
                ranking_option_ids = [item["option"] for item in answer_data.get("ranking_items") or []]
                valid_options_count = Option.objects.filter(
                    question=question,
                    id__in=ranking_option_ids,
                ).count()
                if valid_options_count != len(set(ranking_option_ids)):
                    return DRFResponse(
                        {"detail": f"Question {question.id} contains invalid ranking options"},
                        status=400,
                    )

        with transaction.atomic():
            for a in answers:
                q = Question.objects.select_for_update().get(id=a["question"], survey=resp.survey)
                ans = Answer.objects.create(
                    response=resp,
                    question=q,
                    text=a.get("text", ""),
                    num=a.get("num"),
                )
                if "selected_options" in a:
                    opts = Option.objects.filter(id__in=a["selected_options"], question=q)
                    ans.selected_options.set(opts)
                if "matrix_cells" in a:
                    if q.qtype not in MATRIX_QTYPES:
                        transaction.set_rollback(True)
                        return DRFResponse({"detail": "matrix_cells are allowed only for matrix questions"}, status=400)
                    error = add_matrix_cells(ans, q, a.get("matrix_cells") or [])
                    if error:
                        transaction.set_rollback(True)
                        return DRFResponse({"detail": error}, status=400)
                if "ranking_items" in a:
                    if q.qtype != Question.RANKING:
                        transaction.set_rollback(True)
                        return DRFResponse({"detail": "ranking_items are allowed only for ranking questions"}, status=400)
                    error = add_ranking_items(ans, q, a.get("ranking_items") or [])
                    if error:
                        transaction.set_rollback(True)
                        return DRFResponse({"detail": error}, status=400)

            if terminate_conditions:
                message = next(
                    (
                        condition.terminate_message
                        for condition in terminate_conditions
                        if condition.terminate_message
                    ),
                    "",
                )
                resp.mark_screened_out(message)
                return DRFResponse(
                    {"status": "screened_out", "message": message},
                    status=200,
                )

            resp.mark_completed()
        return DRFResponse({"status":"ok"}, status=200)

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [IsOrganizerOrAdmin]
    @action(detail=False, methods=["get"], url_path="distribution")
    def distribution(self, request):
        ser = AnalyticsSer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        qid=ser.validated_data["question_id"]
        data = question_distribution(qid)
        return DRFResponse(data)
    
    @action(detail=False, methods=["get"], url_path="survey")
    def survey(self, request):
        ser = SurveyAnalyticsSer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        sid = ser.validated_data["survey_id"]
        get_object_or_404(Survey, id=sid, status__in=["draft", "active", "closed"])
        save_flag = request.query_params.get("save") == "true"

        data = survey_distribution(sid, save=save_flag)
        return DRFResponse(data)


class AdvancedAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [IsOrganizerOrAdmin]

    def _check_survey_access(self, request, survey_id):
        if request.user.role == "admin":
            return None
        if Survey.objects.filter(id=survey_id, owners=request.user).exists():
            return None
        return DRFResponse(
            {"detail": "You do not have access to this survey."},
            status=status.HTTP_403_FORBIDDEN,
        )

    def _run(self, request, serializer_class, service):
        ser = serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        access_response = self._check_survey_access(request, ser.validated_data["survey_id"])
        if access_response is not None:
            return access_response
        try:
            data = service(ser.validated_data)
        except ValueError as exc:
            return DRFResponse({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return DRFResponse(data)

    @action(detail=False, methods=["post"], url_path="correlation")
    def correlation(self, request):
        return self._run(request, CorrelationAnalysisSer, run_correlation_analysis)

    @action(detail=False, methods=["post"], url_path="crosstab")
    def crosstab(self, request):
        return self._run(request, CrosstabAnalysisSer, run_crosstab_analysis)

    @action(detail=False, methods=["post"], url_path="chi-square")
    def chi_square(self, request):
        return self._run(request, ChiSquareAnalysisSer, run_chi_square_analysis)

    @action(detail=False, methods=["post"], url_path="correspondence-analysis")
    def correspondence_analysis(self, request):
        return self._run(request, CorrespondenceAnalysisSer, run_correspondence_analysis)

    @action(detail=False, methods=["post"], url_path="regression")
    def regression(self, request):
        return self._run(request, RegressionAnalysisSer, run_regression_analysis)

    @action(detail=False, methods=["post"], url_path="logistic-regression")
    def logistic_regression(self, request):
        return self._run(request, LogisticRegressionSer, run_logistic_regression_analysis)

    @action(detail=False, methods=["post"], url_path="factor-analysis")
    def factor_analysis(self, request):
        return self._run(request, FactorAnalysisSer, run_factor_analysis)

    @action(detail=False, methods=["post"], url_path="cluster-analysis")
    def cluster_analysis(self, request):
        return self._run(request, ClusterAnalysisSer, run_cluster_analysis)

    @action(detail=False, methods=["post"], url_path="group-comparison")
    def group_comparison(self, request):
        return self._run(request, GroupComparisonSer, run_group_comparison)

    @action(detail=False, methods=["post"], url_path="time-analysis")
    def time_analysis(self, request):
        return self._run(request, TimeAnalysisSer, run_time_analysis)

    @action(detail=False, methods=["post"], url_path="reliability")
    def reliability(self, request):
        return self._run(request, ReliabilityAnalysisSer, run_reliability_analysis)

    @action(detail=False, methods=["post"], url_path="scale-index")
    def scale_index(self, request):
        return self._run(request, ScaleIndexSer, run_scale_index_analysis)

    @action(detail=False, methods=["post"], url_path="missing-analysis")
    def missing_analysis(self, request):
        return self._run(request, MissingAnalysisSer, run_missing_analysis)


class AnalyticsExportViewSet(viewsets.ViewSet):
    permission_classes = [IsOrganizerOrAdmin]

    def _check_survey_access(self, request, survey):
        if request.user.role == "admin":
            return
        if not survey.owners.filter(id=request.user.id).exists():
            raise PermissionDenied("You do not have access to this survey.")

    def _get_export_objects(self, request, serializer_class):
        ser = serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        survey = get_object_or_404(Survey, id=data["survey_id"])
        self._check_survey_access(request, survey)

        analytic_result = get_object_or_404(
            AnalyticResults,
            id=data["analytic_result_id"],
            survey=survey,
        )
        analysis_report = get_object_or_404(
            AnalysisReport,
            id=data["analysis_report_id"],
            survey=survey,
        )
        return survey, analytic_result, analysis_report

    @action(detail=False, methods=["post"], url_path="pdf")
    def pdf(self, request):
        survey, analytic_result, analysis_report = self._get_export_objects(request, AnalyticsPdfExportSer)

        try:
            pdf_bytes = build_analytics_pdf(survey, analytic_result, analysis_report)
        except RuntimeError as exc:
            return DRFResponse({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        filename = f"analytics_report_{survey.id}_{timezone.now():%Y%m%d_%H%M}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=["post"], url_path="csv")
    def csv(self, request):
        survey, analytic_result, analysis_report = self._get_export_objects(request, AnalyticsCsvExportSer)

        csv_bytes = build_analytics_csv(survey, analytic_result, analysis_report)
        filename = f"analytics_report_{survey.id}_{timezone.now():%Y%m%d_%H%M}.csv"
        response = HttpResponse(csv_bytes, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=["post"], url_path="xlsx")
    def xlsx(self, request):
        survey, analytic_result, analysis_report = self._get_export_objects(request, AnalyticsXlsxExportSer)

        try:
            xlsx_bytes = build_analytics_xlsx(survey, analytic_result, analysis_report)
        except RuntimeError as exc:
            return DRFResponse({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        filename = f"analytics_report_{survey.id}_{timezone.now():%Y%m%d_%H%M}.xlsx"
        response = HttpResponse(
            xlsx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SurveyResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Ответы пользователей на конкретный опрос
    """
    serializer_class = ResponseReadSer
    permission_classes = [IsOrganizerOrAdmin]

    def get_queryset(self):
        survey_id = self.kwargs["survey_id"]
        return (
            Resp.objects
            .filter(survey_id=survey_id)
            .select_related("user")
            .prefetch_related(
                "answers",
                "answers__selected_options",
                "answers__matrix_cells__row",
                "answers__matrix_cells__column",
                "answers__ranking_items__option",
            )
            .order_by("-finished_at", "-started_at")
        )

    def get_object(self):
        survey_id = self.kwargs["survey_id"]
        response_id = self.kwargs["pk"]
        return get_object_or_404(
            Resp,
            id=response_id,
            survey_id=survey_id,
        )

    def partial_update(self, request, *args, **kwargs):
        resp = self.get_object()
        next_status = request.data.get("status")

        if next_status not in dict(Resp.STATUS):
            return DRFResponse(
                {"detail": "status must be active or blocked"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resp.status = next_status
        resp.save(update_fields=["status"])
        return DRFResponse(self.get_serializer(resp).data)

    def export_csv(self, request, *args, **kwargs):
        survey_id = self.kwargs["survey_id"]
        survey = get_object_or_404(Survey, id=survey_id)
        csv_bytes = build_responses_csv(survey, self.get_queryset())
        filename = f"survey_{survey_id}_responses_{timezone.now():%Y%m%d_%H%M}.csv"
        response = HttpResponse(csv_bytes, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    

class UserViewSet(viewsets.ViewSet):
    """
    Пользователи и профиль пользователя
    """
    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        return [IsAdminRole()]

    def list(self, request):
        qs = User.objects.all().order_by("id")
        ser = UserListSer(qs, many=True)
        return DRFResponse(ser.data)

    def retrieve(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        ser = UserProfileSer(user)
        return DRFResponse(ser.data)

    def partial_update(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)

        # для прототипа считаем, что PATCH /users/{id}/ — админский
        ser = AdminUserUpdateSer(user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()

        return DRFResponse(ser.data)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        user = request.user

        if not user or not user.is_authenticated:
            return DRFResponse(
                {"detail": "Authentication credentials were not provided."},
                status=401
            )

        if request.method == "GET":
            return DRFResponse(UserProfileSer(user).data)

        ser = UserProfileSer(user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return DRFResponse(ser.data)


class AdminSurveyQuestionViewSet(viewsets.ViewSet):
    """
    Bulk-добавление вопросов для опроса
    """
    permission_classes = [IsOrganizerOrAdmin]  # позже IsAdmin

    @action(
        detail=True,
        methods=["post"],
        url_path="questions/bulk",
    )
    def bulk(self, request, pk=None):
        survey = get_object_or_404(Survey, pk=pk)

        if Resp.objects.filter(survey=survey, is_complete=True).exists():
            return DRFResponse(
                {"detail": "Нельзя изменять вопросы опроса, по которому уже есть ответы."},
                status=400,
            )

        ser = BulkQuestionsSer(data=request.data)
        ser.is_valid(raise_exception=True)
        questions_data = ser.validated_data["questions"]

        with transaction.atomic():
            # 1. Удаляем старые вопросы
            survey.questions.all().delete()

            # 2. Создаём новые
            for order, qd in enumerate(questions_data):
                question = Question.objects.create(
                    survey=survey,
                    text=qd["text"],
                    qtype=qd["qtype"],
                    order=order,
                    required=qd.get("required", True),
                    qsettings=qd.get("qsettings", {}),
                    randomize_options=qd.get("randomize_options", False),
                )

                create_question_items(question, qd)

        return DRFResponse(
            {"status": "ok", "questions_count": len(questions_data)},
            status=200,
        )
    
class AdminSurveyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOrganizerOrAdmin]

    def get_queryset(self):
        qs = (
            Survey.objects
            .annotate(
                questions_count=Count("questions", distinct=True),
                responses_count=Count("responses", distinct=True),
            )
            .order_by("-created_at")
        )
        if self.request.user.role == "admin":
            return qs
        return qs.filter(owners=self.request.user)

    def perform_create(self, serializer):
        survey = serializer.save()
        survey.owners.add(self.request.user)

    def destroy(self, request, *args, **kwargs):
        survey = self.get_object()
        delete_responses = request.query_params.get("delete_responses") == "true"

        if not delete_responses:
            survey.status = "deleted"
            survey.save(update_fields=["status"])
            return DRFResponse(
                {"status": "deleted"},
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            survey.responses.all().delete()
            survey.produces.all().delete()
            survey.delete()

        return DRFResponse(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if self.action == "list":
            return AdminSurveyListSer
        elif self.action == "retrieve":
            return AdminSurveyDetailSer
        return SurveyCreateUpdateSer

    @action(detail=True, methods=["post"], url_path="pages/bulk")
    def bulk_pages(self, request, pk=None):
        survey = self.get_object()

        if Resp.objects.filter(survey=survey, is_complete=True).exists():
            return DRFResponse(
                {"detail": "Нельзя изменять структуру опроса, по которому уже есть ответы."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = BulkSurveyPagesSer(data=request.data)
        ser.is_valid(raise_exception=True)
        pages_data = ser.validated_data["pages"]

        with transaction.atomic():
            survey.questions.all().delete()
            survey.pages.all().delete()

            for page_index, page_data in enumerate(pages_data):
                page = SurveyPage.objects.create(
                    survey=survey,
                    title=page_data.get("title", ""),
                    description=page_data.get("description", ""),
                    order=page_data.get("order", page_index),
                    randomize_questions=page_data.get("randomize_questions", False),
                )

                for question_index, qd in enumerate(page_data.get("questions", [])):
                    question = Question.objects.create(
                        survey=survey,
                        page=page,
                        text=qd["text"],
                        qtype=qd["qtype"],
                        order=qd.get("order", question_index),
                        required=qd.get("required", True),
                        qsettings=qd.get("qsettings", {}),
                        randomize_options=qd.get("randomize_options", False),
                    )

                    create_question_items(question, qd)

        survey = self.get_queryset().get(pk=survey.pk)
        return DRFResponse(AdminSurveyDetailSer(survey).data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["post"], url_path="conditions/bulk")
    def bulk_conditions(self, request, pk=None):
        survey = self.get_object()

        if Resp.objects.filter(survey=survey, is_complete=True).exists():
            return DRFResponse(
                {"detail": "Нельзя изменять логику ветвления опроса, по которому уже есть ответы."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = BulkQuestionConditionsSer(data=request.data)
        ser.is_valid(raise_exception=True)
        conditions_data = ser.validated_data["conditions"]

        with transaction.atomic():
            QuestionCondition.objects.filter(source_question__survey=survey).delete()
            QuestionConditionGroup.objects.filter(survey=survey).delete()

            for cd in conditions_data:
                cd.pop("group", None)
                group_key = cd.pop("group_key", "")
                group_title = cd.pop("group_title", "") or group_key
                group_logic = cd.pop("group_logic", "all")
                if group_title and not cd.get("group"):
                    group, _ = QuestionConditionGroup.objects.get_or_create(
                        survey=survey,
                        title=group_title,
                        defaults={
                            "logic": group_logic,
                            "priority": cd.get("priority", 0),
                            "is_active": cd.get("is_active", True),
                        },
                    )
                    if group.logic != group_logic:
                        group.logic = group_logic
                        group.save(update_fields=["logic"])
                    cd["group"] = group
                condition = QuestionCondition(**cd)
                condition.full_clean()
                condition.save()

        qs = (
            QuestionCondition.objects
            .filter(source_question__survey=survey)
            .select_related("source_question", "question", "page", "target_page", "option", "matrix_row", "matrix_column", "group")
            .order_by("priority", "id")
        )
        return DRFResponse(
            {"conditions": QuestionConditionReadSer(qs, many=True).data},
            status=status.HTTP_200_OK,
        )


class AnalysisReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOrganizerOrAdmin]

    def get_queryset(self):
        qs = AnalysisReport.objects.select_related("survey", "created_by")
        if self.request.user.role == "admin":
            return qs
        return qs.filter(survey__owners=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return AnalysisReportListSer
        if self.action == "create":
            return AnalysisReportCreateSer
        return AnalysisReportDetailSer

    def perform_create(self, serializer):
        survey = serializer.validated_data["survey"]

        if self.request.user.role != "admin" and not survey.owners.filter(id=self.request.user.id).exists():
            raise PermissionDenied("You do not have access to this survey.")

        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="chart")
    def chart(self, request, pk=None):
        report = self.get_object()
        section_id = request.data.get("section_id")
        chart_type = request.data.get("chart_type")

        if not section_id:
            return DRFResponse(
                {"detail": "section_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            buffer = build_report_section_chart(
                report=report,
                section_id=section_id,
                chart_type=chart_type,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            return DRFResponse(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = HttpResponse(buffer.getvalue(), content_type="image/png")
        response["Content-Disposition"] = 'inline; filename="analysis-chart.png"'
        return response

class AnalyticResultsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOrganizerOrAdmin]

    def get_queryset(self):
        qs = AnalyticResults.objects.select_related("survey")
        survey_id = self.request.query_params.get("survey_id")
        if survey_id:
            qs = qs.filter(survey_id=survey_id)

        if self.request.user.role == "admin":
            return qs
        return qs.filter(survey__owners=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return AnalyticResultsListSer
        return AnalyticResultsDetailSer

    def create(self, request):
        survey_id = request.data.get("survey_id")
        title = request.data.get("title") or f"Срез аналитики от {timezone.now():%d.%m.%Y %H:%M}"

        survey = get_object_or_404(Survey, id=survey_id)

        if request.user.role != "admin" and not survey.owners.filter(id=request.user.id).exists():
            raise PermissionDenied("You do not have access to this survey.")

        data = survey_distribution(survey.id, save=False)

        snapshot = AnalyticResults.objects.create(
            survey=survey,
            title=title,
            total_responses=data["summary"]["total_finished"],
            data=data,
        )

        return DRFResponse(
            AnalyticResultsDetailSer(snapshot).data,
            status=status.HTTP_201_CREATED,
        )
