# surveys/views.py
import secrets, datetime as dt
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from .models import (
    Survey,
    Response as Resp,
    Answer,
    Question,
    QuestionCondition,
    Option,
    SurveyPage,
    MatrixRow,
    MatrixColumn,
    MatrixAnswerCell,
    RankingAnswerItem,
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
from .permissions import IsAdminRole, IsOrganizerOrAdmin, IsOrganizer
from .analytics import question_distribution, survey_distribution
from .advanced_analytics_serializers import (
    ChiSquareAnalysisSer,
    ClusterAnalysisSer,
    CorrelationAnalysisSer,
    CrosstabAnalysisSer,
    FactorAnalysisSer,
    RegressionAnalysisSer,
)
from .advanced_analytics_services import (
    run_chi_square_analysis,
    run_cluster_analysis,
    run_correlation_analysis,
    run_crosstab_analysis,
    run_factor_analysis,
    run_regression_analysis,
)
from .pdf_export import build_analytics_pdf
from .csv_export import build_analytics_csv
from .xlsx_export import build_analytics_xlsx

User = get_user_model()

MATRIX_QTYPES = {Question.MATRIX_SINGLE, Question.MATRIX_MULTI}
CHOICE_QTYPES = {Question.SINGLE, Question.DROPDOWN, Question.YESNO}
MULTI_CHOICE_QTYPES = {Question.MULTI}
TEXT_QTYPES = {Question.TEXT, Question.DATE}
NUMERIC_QTYPES = {Question.SCALE, Question.NUMBER}
RANKING_QTYPES = {Question.RANKING}

ANSWER_FIELDS = {"selected_options", "text", "num", "matrix_cells", "ranking_items"}
ALLOWED_ANSWER_FIELDS = {
    Question.SINGLE: {"selected_options"},
    Question.DROPDOWN: {"selected_options"},
    Question.YESNO: {"selected_options"},
    Question.MULTI: {"selected_options"},
    Question.TEXT: {"text"},
    Question.DATE: {"text"},
    Question.SCALE: {"num"},
    Question.NUMBER: {"num"},
    Question.MATRIX_SINGLE: {"matrix_cells"},
    Question.MATRIX_MULTI: {"matrix_cells"},
    Question.RANKING: {"ranking_items"},
}

YESNO_DEFAULT_OPTIONS = (
    {"text": "Да", "value": "yes", "order": 0},
    {"text": "Нет", "value": "no", "order": 1},
)


def create_question_items(question, question_data):
    options = question_data.get("options", [])
    if question.qtype == Question.YESNO and not options:
        options = YESNO_DEFAULT_OPTIONS

    for opt_order, opt in enumerate(options):
        Option.objects.create(
            question=question,
            text=opt["text"],
            value=opt.get("value", ""),
            order=opt.get("order", opt_order),
        )

    for row_order, row in enumerate(question_data.get("matrix_rows", [])):
        MatrixRow.objects.create(
            question=question,
            text=row["text"],
            value=row.get("value", ""),
            order=row.get("order", row_order),
        )

    for column_order, column in enumerate(question_data.get("matrix_columns", [])):
        MatrixColumn.objects.create(
            question=question,
            text=column["text"],
            value=column.get("value", ""),
            order=column.get("order", column_order),
        )


def add_matrix_cells(answer, question, cells_data):
    if not isinstance(cells_data, list):
        return "matrix_cells must be a list"
    if any(not isinstance(cell, dict) for cell in cells_data):
        return "matrix_cells must contain objects"

    rows = {
        row.id: row
        for row in MatrixRow.objects.filter(question=question, id__in=[cell.get("row") for cell in cells_data])
    }
    columns = {
        column.id: column
        for column in MatrixColumn.objects.filter(question=question, id__in=[cell.get("column") for cell in cells_data])
    }

    seen_pairs = set()
    seen_rows = set()
    cells = []
    for cell in cells_data:
        row_id = cell.get("row")
        column_id = cell.get("column")
        if row_id not in rows or column_id not in columns:
            return "matrix row or column does not belong to question"

        pair = (row_id, column_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        if question.qtype == Question.MATRIX_SINGLE:
            if row_id in seen_rows:
                return "matrix_single allows only one column per row"
            seen_rows.add(row_id)

        cell_obj = MatrixAnswerCell(answer=answer, row=rows[row_id], column=columns[column_id])
        cell_obj.full_clean()
        cells.append(cell_obj)

    MatrixAnswerCell.objects.bulk_create(cells)
    return None


def is_full_ranking_question(question):
    return question.qsettings.get("full_ranking", True)


def add_ranking_items(answer, question, items_data):
    options = {
        option.id: option
        for option in Option.objects.filter(question=question, id__in=[item.get("option") for item in items_data])
    }

    ranking_items = []
    for item in items_data:
        option_id = item.get("option")
        if option_id not in options:
            return "ranking option does not belong to question"

        ranking_item = RankingAnswerItem(
            answer=answer,
            option=options[option_id],
            rank=item["rank"],
        )
        ranking_item.full_clean()
        ranking_items.append(ranking_item)

    RankingAnswerItem.objects.bulk_create(ranking_items)
    return None


def answer_has_value(question, answer_data):
    if question.qtype in CHOICE_QTYPES | MULTI_CHOICE_QTYPES:
        return bool(answer_data.get("selected_options"))
    if question.qtype in TEXT_QTYPES:
        return bool((answer_data.get("text") or "").strip())
    if question.qtype in NUMERIC_QTYPES:
        return answer_data.get("num") is not None
    if question.qtype in MATRIX_QTYPES:
        return bool(answer_data.get("matrix_cells"))
    if question.qtype in RANKING_QTYPES:
        return bool(answer_data.get("ranking_items"))
    return False


def extract_answer_value(question, answer_data):
    if not answer_data:
        return None
    if question.qtype in CHOICE_QTYPES:
        selected_options = answer_data.get("selected_options") or []
        return selected_options[0] if selected_options else None
    if question.qtype in MULTI_CHOICE_QTYPES:
        return answer_data.get("selected_options") or []
    if question.qtype in TEXT_QTYPES:
        return (answer_data.get("text") or "").strip()
    if question.qtype in NUMERIC_QTYPES:
        return answer_data.get("num")
    if question.qtype in MATRIX_QTYPES:
        return answer_data.get("matrix_cells") or []
    if question.qtype in RANKING_QTYPES:
        return answer_data.get("ranking_items") or []
    return None


def condition_matches(condition, source_question, answer_data):
    operator = condition.operator

    if operator == "is_answered":
        return bool(answer_data) and answer_has_value(source_question, answer_data)
    if operator == "not_answered":
        return not answer_data or not answer_has_value(source_question, answer_data)

    value = extract_answer_value(source_question, answer_data)

    if operator == "contains_option":
        if not condition.option_id:
            return False
        if source_question.qtype in CHOICE_QTYPES:
            return value == condition.option_id
        if source_question.qtype in MULTI_CHOICE_QTYPES:
            return condition.option_id in value
        return False

    if operator in ("equals", "not_equals"):
        if condition.option_id:
            expected = condition.option_id
        elif condition.value_number is not None:
            expected = condition.value_number
        else:
            expected = condition.value_text
        result = value == expected
        return result if operator == "equals" else not result

    if operator in ("gt", "lt", "gte", "lte"):
        if value is None or condition.value_number is None:
            return False
        try:
            value = float(value)
        except (TypeError, ValueError):
            return False
        if operator == "gt":
            return value > condition.value_number
        if operator == "lt":
            return value < condition.value_number
        if operator == "gte":
            return value >= condition.value_number
        if operator == "lte":
            return value <= condition.value_number

    return False


def evaluate_conditions(conditions, answers_by_question, questions_by_id):
    groups = {}
    for index, condition in enumerate(conditions):
        group_key = condition.group_key or f"__condition_{condition.id or index}"
        groups.setdefault(group_key, []).append(condition)

    matched_conditions = []
    for group_conditions in groups.values():
        group_results = []
        for condition in group_conditions:
            source_question = questions_by_id.get(condition.source_question_id)
            if not source_question:
                group_results.append((condition, False))
                continue

            answer_data = answers_by_question.get(condition.source_question_id)
            group_results.append((
                condition,
                condition_matches(condition, source_question, answer_data),
            ))

        group_logic = group_conditions[0].group_logic
        if group_logic == "any":
            matched_conditions.extend(
                condition for condition, matches in group_results if matches
            )
        elif all(matches for _, matches in group_results):
            matched_conditions.extend(group_conditions)

    return matched_conditions


def validate_answer_payload(question, answer_data):
    present_fields = {field for field in ANSWER_FIELDS if field in answer_data}
    allowed_fields = ALLOWED_ANSWER_FIELDS.get(question.qtype, set())
    disallowed_fields = present_fields - allowed_fields

    if disallowed_fields:
        fields = ", ".join(sorted(disallowed_fields))
        return f"Question {question.id} ({question.qtype}) does not allow fields: {fields}"

    if question.required and not answer_has_value(question, answer_data):
        return f"Question {question.id} is required"

    if question.qtype in CHOICE_QTYPES:
        selected_options = answer_data.get("selected_options", [])
        if len(selected_options) > 1:
            return f"Question {question.id} allows only one selected option"

    if question.qtype in CHOICE_QTYPES | MULTI_CHOICE_QTYPES and "selected_options" in answer_data:
        selected_options = answer_data.get("selected_options") or []
        if len(selected_options) != len(set(selected_options)):
            return f"Question {question.id} contains duplicate selected options"

    if question.qtype in MATRIX_QTYPES and "matrix_cells" not in answer_data and question.required:
        return f"Question {question.id} is required"

    if question.qtype == Question.RANKING and "ranking_items" in answer_data:
        ranking_items = answer_data.get("ranking_items") or []
        option_ids = [item["option"] for item in ranking_items]
        ranks = [item["rank"] for item in ranking_items]

        if len(option_ids) != len(set(option_ids)):
            return f"Question {question.id} contains duplicate ranking options"
        if len(ranks) != len(set(ranks)):
            return f"Question {question.id} contains duplicate ranks"

        options_count = question.options.count()
        if is_full_ranking_question(question):
            if len(ranking_items) != options_count:
                return f"Question {question.id} requires ranking all options"
            if set(ranks) != set(range(1, options_count + 1)):
                return f"Question {question.id} requires ranks from 1 to {options_count}"

    return None

class SurveyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Survey.objects.all()
    def get_permissions(self):
        return [AllowAny()] if self.action in ["list","retrieve"] else [IsAuthenticated()]

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

    @action(detail=False, methods=["post"], url_path="submit")
    def submit(self, request):
        ser = SubmitAnswerSer(data=request.data); ser.is_valid(raise_exception=True)
        token = ser.validated_data["response_token"]
        answers = ser.validated_data["answers"]
        try:
            resp = Resp.objects.get(session_token=token, is_complete=False)
        except Resp.DoesNotExist:
            return DRFResponse({"detail":"invalid or completed token"}, status=400)

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
            .select_related("source_question", "question", "page", "target_page", "option")
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

    @action(detail=False, methods=["post"], url_path="regression")
    def regression(self, request):
        return self._run(request, RegressionAnalysisSer, run_regression_analysis)

    @action(detail=False, methods=["post"], url_path="factor-analysis")
    def factor_analysis(self, request):
        return self._run(request, FactorAnalysisSer, run_factor_analysis)

    @action(detail=False, methods=["post"], url_path="cluster-analysis")
    def cluster_analysis(self, request):
        return self._run(request, ClusterAnalysisSer, run_cluster_analysis)


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

            for cd in conditions_data:
                condition = QuestionCondition(**cd)
                condition.full_clean()
                condition.save()

        qs = (
            QuestionCondition.objects
            .filter(source_question__survey=survey)
            .select_related("source_question", "question", "page", "target_page", "option")
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
