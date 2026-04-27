from rest_framework import serializers
from .models import (
    Survey,
    Question,
    QuestionCondition,
    Option,
    Response,
    Answer,
    SurveyPage,
    MatrixRow,
    MatrixColumn,
    MatrixAnswerCell,
    RankingAnswerItem,
    AnalysisReport,
)
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class OptionSer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ("id","text","value","order")


class MatrixRowSer(serializers.ModelSerializer):
    class Meta:
        model = MatrixRow
        fields = ("id", "text", "value", "order")


class MatrixColumnSer(serializers.ModelSerializer):
    class Meta:
        model = MatrixColumn
        fields = ("id", "text", "value", "order")


class MatrixAnswerCellReadSer(serializers.ModelSerializer):
    row_text = serializers.CharField(source="row.text", read_only=True)
    column_text = serializers.CharField(source="column.text", read_only=True)

    class Meta:
        model = MatrixAnswerCell
        fields = ("id", "row", "row_text", "column", "column_text")


class RankingAnswerItemReadSer(serializers.ModelSerializer):
    option_text = serializers.CharField(source="option.text", read_only=True)

    class Meta:
        model = RankingAnswerItem
        fields = ("id", "option", "option_text", "rank")


class QuestionSer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    matrix_rows = serializers.SerializerMethodField()
    matrix_columns = serializers.SerializerMethodField()
    conditions = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            "id",
            "text",
            "qtype",
            "order",
            "required",
            "options",
            "matrix_rows",
            "matrix_columns",
            "conditions",
            "qsettings",
            "page",
            "randomize_options",
        )

    def get_conditions(self, obj):
        qs = obj.conditions.filter(is_active=True).order_by("priority", "id")
        return QuestionConditionReadSer(qs, many=True).data

    def get_options(self, obj):
        return OptionSer(obj.options.all().order_by("order", "id"), many=True).data

    def get_matrix_rows(self, obj):
        return MatrixRowSer(obj.matrix_rows.all().order_by("order", "id"), many=True).data

    def get_matrix_columns(self, obj):
        return MatrixColumnSer(obj.matrix_columns.all().order_by("order", "id"), many=True).data


class SurveyPageSer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    conditions = serializers.SerializerMethodField()

    class Meta:
        model = SurveyPage
        fields = ("id", 
                "title", 
                "description", 
                "order", 
                "randomize_questions",
                "conditions",
                "questions")

    def get_questions(self, obj):
        questions = obj.question_page.all().order_by("order", "id")
        return QuestionSer(questions, many=True).data
    
    def get_conditions(self, obj):
        qs = obj.conditions.filter(is_active=True).order_by("priority", "id")
        return QuestionConditionReadSer(qs, many=True).data


class SurveyListSer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ("id","title","description","status","starts_at","ends_at")

class SurveyDetailSer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    pages = serializers.SerializerMethodField()
    conditions = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = ("id","title","description","is_anonymous","randomize_pages","questions","pages","conditions")

    def get_questions(self, obj):
        questions = obj.questions.all().order_by("order", "id")
        return QuestionSer(questions, many=True).data

    def get_pages(self, obj):
        pages = obj.pages.all().order_by("order", "id")
        return SurveyPageSer(pages, many=True).data

    def get_conditions(self, obj):
        qs = (
            QuestionCondition.objects
            .filter(source_question__survey=obj, is_active=True)
            .select_related("source_question", "question", "page", "target_page", "option")
            .order_by("priority", "id")
        )
        return QuestionConditionReadSer(qs, many=True).data

class StartResponseSer(serializers.Serializer):
    survey_id = serializers.IntegerField()


class MatrixAnswerCellWriteSer(serializers.Serializer):
    row = serializers.IntegerField()
    column = serializers.IntegerField()


class RankingAnswerItemWriteSer(serializers.Serializer):
    option = serializers.IntegerField()
    rank = serializers.IntegerField(min_value=1)


class SubmitAnswerItemSer(serializers.Serializer):
    question = serializers.IntegerField()
    selected_options = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )
    text = serializers.CharField(required=False, allow_blank=True)
    num = serializers.FloatField(required=False, allow_null=True)
    matrix_cells = MatrixAnswerCellWriteSer(many=True, required=False)
    ranking_items = RankingAnswerItemWriteSer(many=True, required=False)


class SubmitAnswerSer(serializers.Serializer):
    response_token = serializers.CharField()
    answers = SubmitAnswerItemSer(many=True, allow_empty=False)

class AnalyticsSer(serializers.Serializer):
    question_id = serializers.IntegerField()

class SurveyAnalyticsSer(serializers.Serializer):
    survey_id = serializers.IntegerField()

class AnswerReadSer(serializers.ModelSerializer):
    selected_options = serializers.SerializerMethodField()
    matrix_cells = MatrixAnswerCellReadSer(many=True, read_only=True)
    ranking_items = RankingAnswerItemReadSer(many=True, read_only=True)

    class Meta:
        model = Answer
        fields = ("id", "question", "text", "num", "selected_options", "matrix_cells", "ranking_items")

    def get_selected_options(self, obj):
        return [
            {"id": o.id, "text": o.text}
            for o in obj.selected_options.all()
        ]


class ResponseReadSer(serializers.ModelSerializer):
    answers = AnswerReadSer(many=True, read_only=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = Response
        fields = (
            "id",
            "user",
            "started_at",
            "finished_at",
            "is_complete",
            "status",
            "screened_out",
            "screened_out_at",
            "screened_out_reason",
            "complete_reason",
            "answers",
        )

    def get_user(self, obj):
        if obj.user:
            return {
                "id": obj.user.id,
                "username": obj.user.username,
                "email": obj.user.email,
            }
        return None

class UserListSer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "role",
            "date_joined",
        )


class UserProfileSer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "role",
            "date_joined",
        )
        read_only_fields = ("id", "username", "is_active", "role", "date_joined")

class AdminUserUpdateSer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "is_active",
            "role",
        )

class SurveyCreateUpdateSer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = (
            "id",
            "title",
            "description",
            "status",
            "starts_at",
            "ends_at",
            "is_anonymous",
            "randomize_pages",
        )

class OptionCreateSer(serializers.Serializer):
    text = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=64, required=False, allow_blank=True)
    order = serializers.IntegerField(required=False, min_value=0)


class MatrixRowCreateSer(serializers.Serializer):
    text = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=64, required=False, allow_blank=True)
    order = serializers.IntegerField(required=False, min_value=0)


class MatrixColumnCreateSer(serializers.Serializer):
    text = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=64, required=False, allow_blank=True)
    order = serializers.IntegerField(required=False, min_value=0)


class QuestionCreateSer(serializers.Serializer):
    text = serializers.CharField()
    qtype = serializers.ChoiceField(
        choices=[
            "single",
            "multi",
            "text",
            "scale",
            "dropdown",
            "yesno",
            "number",
            "date",
            "matrix_single",
            "matrix_multi",
            "ranking",
        ]
    )
    required = serializers.BooleanField(default=True)
    qsettings = serializers.JSONField(required=False)
    order = serializers.IntegerField(required=False, min_value=0)
    randomize_options = serializers.BooleanField(default=False)
    options = OptionCreateSer(many=True, required=False)
    matrix_rows = MatrixRowCreateSer(many=True, required=False)
    matrix_columns = MatrixColumnCreateSer(many=True, required=False)

    def validate(self, attrs):
        qtype = attrs.get("qtype")
        is_matrix = qtype in ("matrix_single", "matrix_multi")
        has_options = "options" in attrs and bool(attrs.get("options"))
        has_matrix_rows = "matrix_rows" in attrs and bool(attrs.get("matrix_rows"))
        has_matrix_columns = "matrix_columns" in attrs and bool(attrs.get("matrix_columns"))

        if is_matrix:
            if not has_matrix_rows or not has_matrix_columns:
                raise serializers.ValidationError(
                    "Matrix questions must include matrix_rows and matrix_columns."
                )
            if has_options:
                raise serializers.ValidationError("Matrix questions cannot include options.")
            return attrs

        if has_matrix_rows or has_matrix_columns:
            raise serializers.ValidationError(
                "Only matrix questions can include matrix_rows or matrix_columns."
            )

        if qtype in ("single", "multi", "dropdown", "ranking") and not has_options:
            raise serializers.ValidationError(f"{qtype} questions must include at least one option.")

        if qtype == "yesno":
            if has_options and len(attrs.get("options", [])) != 2:
                raise serializers.ValidationError("yesno questions must include exactly two options.")
            return attrs

        if qtype in ("text", "date", "number", "scale") and has_options:
            raise serializers.ValidationError(f"{qtype} questions cannot include options.")

        return attrs


class BulkQuestionsSer(serializers.Serializer):
    questions = QuestionCreateSer(many=True)


class SurveyPageCreateSer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    order = serializers.IntegerField(required=False, min_value=0)
    randomize_questions = serializers.BooleanField(default=False)
    questions = QuestionCreateSer(many=True, required=False)


class BulkSurveyPagesSer(serializers.Serializer):
    pages = SurveyPageCreateSer(many=True)


class AdminSurveyListSer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    questions_count = serializers.IntegerField(read_only=True)
    responses_count = serializers.IntegerField(read_only=True)
    starts_at = serializers.DateTimeField(format="%Y-%m-%d")
    

    class Meta:
        model = Survey
        fields = (
            "id",
            "title",
            "description",
            "status",
            "author",
            "questions_count",
            "responses_count",
            "starts_at",
            "created_at",
        )

    def get_author(self, obj):
        # если есть owners M2M
        owners = obj.owners.all()
        if owners.exists():
            return owners.first().email
        return None

class AdminSurveyDetailSer(serializers.ModelSerializer):
    questions = QuestionSer(many=True, read_only=True)
    pages = SurveyPageSer(many=True, read_only=True)
    conditions = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = (
            "id",
            "title",
            "description",
            "status",
            "starts_at",
            "ends_at",
            "is_anonymous",
            "randomize_pages",
            "questions",
            "pages",
            "conditions",
        )

    def get_conditions(self, obj):
        qs = (
            QuestionCondition.objects
            .filter(source_question__survey=obj)
            .select_related("source_question", "question", "page", "target_page", "option")
            .order_by("priority", "id")
        )
        return QuestionConditionReadSer(qs, many=True).data

class ResponseStatusUpdateSer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = (
            "status",
            "screened_out",
            "screened_out_reason",
            "complete_reason",
        )

class QuestionConditionReadSer(serializers.ModelSerializer):
    source_question_text = serializers.CharField(source="source_question.text", read_only=True)
    question_text = serializers.CharField(source="question.text", read_only=True)
    page_title = serializers.CharField(source="page.title", read_only=True)
    target_page_title = serializers.CharField(source="target_page.title", read_only=True)
    option_text = serializers.CharField(source="option.text", read_only=True)

    class Meta:
        model = QuestionCondition
        fields = (
            "id",
            "source_question",
            "source_question_text",
            "question",
            "question_text",
            "page",
            "page_title",
            "action",
            "target_page",
            "target_page_title",
            "operator",
            "value_text",
            "value_number",
            "option",
            "option_text",
            "group_key",
            "group_logic",
            "priority",
            "is_active",
            "terminate_message",
        )

class QuestionConditionWriteSer(serializers.ModelSerializer):
    class Meta:
        model = QuestionCondition
        fields = (
            "id",
            "source_question",
            "question",
            "page",
            "action",
            "target_page",
            "operator",
            "value_text",
            "value_number",
            "option",
            "group_key",
            "group_logic",
            "priority",
            "is_active",
            "terminate_message",
        )

    def validate(self, attrs):
        instance = QuestionCondition(**attrs)
        try:
            instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, "message_dict") else e.messages)
        return attrs

class BulkQuestionConditionsSer(serializers.Serializer):
    conditions = QuestionConditionWriteSer(many=True)


class AnalysisReportListSer(serializers.ModelSerializer):
    survey_title = serializers.CharField(source="survey.title", read_only=True)

    class Meta:
        model = AnalysisReport
        fields = (
            "id",
            "survey",
            "survey_title",
            "title",
            "created_at",
            "updated_at",
        )


class AnalysisReportDetailSer(serializers.ModelSerializer):
    survey_title = serializers.CharField(source="survey.title", read_only=True)

    class Meta:
        model = AnalysisReport
        fields = (
            "id",
            "survey",
            "survey_title",
            "title",
            "config",
            "result",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_by", "created_at", "updated_at")


class AnalysisReportCreateSer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisReport
        fields = (
            "survey",
            "title",
            "config",
            "result",
        )