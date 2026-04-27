from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class Survey(models.Model):
    STATUS = (("draft","Draft"), ("active","Active"), ("closed","Closed"))
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    owners = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="owned_surveys", blank=True)
    is_anonymous = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    randomize_pages = models.BooleanField(default=False)

class SurveyPage(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="pages")
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    randomize_questions = models.BooleanField(default=False)

class Question(models.Model):
    SINGLE="single"; MULTI="multi"; TEXT="text" 
    SCALE="scale"; DROPDOWN="dropdown"; YESNO="yesno" 
    NUMBER="number"; DATE="date"; RANKING="ranking"
    MATRIX_SINGLE="matrix_single"; MATRIX_MULTI="matrix_multi"
    QTYPE=((SINGLE,"Single"),(MULTI,"Multi"),(TEXT,"Text"),(SCALE,"Scale"),
        (DROPDOWN,"Dropdown"),(YESNO,"Yes/No"),(NUMBER,"Number"),(DATE,"Date"),
        (MATRIX_SINGLE,"Matrix Single"),(MATRIX_MULTI, "Matrix Multi"),(RANKING, "Ranking"))
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
    page = models.ForeignKey(SurveyPage, on_delete=models.CASCADE, related_name="question_page", null=True, blank=True)
    text = models.TextField()
    short_label = models.CharField(max_length=100, blank=True, default='')
    qtype = models.CharField(max_length=15, choices=QTYPE, default=SINGLE)
    order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)
    randomize_options = models.BooleanField(default=False)
    qsettings = models.JSONField(max_length=100, blank=True, default=dict)

class QuestionCondition(models.Model):
    OPERATOR_CHOICES=[
            ("equals", "Equals"),
            ("not_equals", "Not equals"),
            ("contains_option", "Contains option"),
            ("gt", "Greater than"),
            ("lt", "Less than"),
            ("gte", "Greater than or equal"),
            ("lte", "Less than or equal"),
            ("is_answered", "Is answered"),
            ("not_answered", "Not answered"),
        ]
    
    ACTION_CHOICES = [
        ("show_question", "Show question"),
        ("show_page", "Show page"),
        ("jump_to_page", "Jump to page"),
        ("terminate", "Terminate survey"),
    ]

    LOGIC_CHOICES = [
        ("all", "All conditions in group must match"),
        ("any", "Any condition in group may match"),
    ]
    # Источник условия: ответ на какой вопрос проверяем
    source_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="outgoing_conditions")
    # Что именно управляется этим условием:
    # либо конкретный вопрос,
    # либо страница,
    # либо только действие terminate / jump_to_page
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="conditions", null=True, blank=True)
    page = models.ForeignKey(SurveyPage, on_delete=models.CASCADE, related_name="conditions", null=True, blank=True)
    # Какое действие выполняется при срабатывании условия
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, default="show_question")
    # Для перехода на страницу
    target_page = models.ForeignKey(SurveyPage, on_delete=models.CASCADE, related_name="incoming_conditions", null=True, blank=True)
    # Условие сравнения
    operator=models.CharField(max_length=32, choices=OPERATOR_CHOICES)
    value_text = models.TextField(blank=True, default='')
    value_number = models.FloatField(null=True, blank=True)
    option = models.ForeignKey("Option", on_delete=models.CASCADE, null=True, blank=True)
    # Для группировки нескольких условий в одно правило
    # Например: group_key="screenout_1", group_logic="all"
    group_key = models.CharField(max_length=64, blank=True, default="")
    group_logic = models.CharField(max_length=8, choices=LOGIC_CHOICES, default="all")
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Сообщение для скрининга
    terminate_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["priority", "id"]

    def clean(self):
        super().clean()

        # Должна быть выбрана одна целевая сущность или специальное действие
        target_count = sum([
            1 if self.question_id else 0,
            1 if self.page_id else 0,
        ])

        if self.action in ("show_question", "show_page"):
            if target_count != 1:
                raise ValidationError(
                    "For show_question/show_page exactly one of 'question' or 'page' must be set."
                )
            if self.action == "show_question" and not self.question_id:
                raise ValidationError({"question": "question is required for show_question"})
            if self.action == "show_page" and not self.page_id:
                raise ValidationError({"page": "page is required for show_page"})
            if self.target_page_id:
                raise ValidationError({"target_page": "target_page is not allowed for show actions"})

        elif self.action == "jump_to_page":
            if target_count != 0:
                raise ValidationError(
                    "For jump_to_page do not set 'question' or 'page'; use only target_page."
                )
            if not self.target_page_id:
                raise ValidationError({"target_page": "target_page is required for jump_to_page"})

        elif self.action == "terminate":
            if target_count != 0 or self.target_page_id:
                raise ValidationError(
                    "For terminate do not set question, page, or target_page."
                )

        # Проверка согласованности survey
        survey_id = self.source_question.survey_id if self.source_question_id else None

        if self.question_id and self.question.survey_id != survey_id:
            raise ValidationError({"question": "question must belong to the same survey as source_question"})

        if self.page_id and self.page.survey_id != survey_id:
            raise ValidationError({"page": "page must belong to the same survey as source_question"})

        if self.target_page_id and self.target_page.survey_id != survey_id:
            raise ValidationError({"target_page": "target_page must belong to the same survey as source_question"})

        if self.option_id and self.option.question_id != self.source_question_id:
            raise ValidationError({"option": "option must belong to source_question"})

        # Проверка типа значения для операторов
        if self.operator in ("contains_option",) and not self.option_id:
            raise ValidationError({"option": "option is required for contains_option"})

        if self.operator in ("gt", "lt", "gte", "lte") and self.value_number is None:
            raise ValidationError({"value_number": "value_number is required for numeric operators"})

        if self.operator in ("equals", "not_equals"):
            if self.option_id is None and self.value_number is None and not self.value_text:
                raise ValidationError(
                    "For equals/not_equals specify one of option, value_number, or value_text."
                )

        if self.operator in ("is_answered", "not_answered"):
            if self.option_id or self.value_text or self.value_number is not None:
                raise ValidationError(
                    "is_answered/not_answered must not use option, value_text, or value_number."
                )

        if self.action == "terminate" and self.terminate_message and len(self.terminate_message) > 2000:
            raise ValidationError({"terminate_message": "terminate_message is too long"})

    def __str__(self):
        return f"{self.action} from question {self.source_question_id}"

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    value = models.CharField(max_length=64, blank=True)  # код варианта
    order = models.PositiveIntegerField(default=0)

class RankingAnswerItem(models.Model):
    answer = models.ForeignKey("Answer", on_delete=models.CASCADE, related_name="ranking_items")
    option = models.ForeignKey(Option, on_delete=models.CASCADE)
    rank = models.PositiveIntegerField()

    def clean(self):
        super().clean()
        if self.answer_id and self.option_id and self.option.question_id != self.answer.question_id:
            raise ValidationError({"option": "Ranking option must belong to the answer question."})
        if self.rank < 1:
            raise ValidationError({"rank": "Rank must be greater than zero."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["answer", "option"], name="unique_ranking_option_per_answer"),
            models.UniqueConstraint(fields=["answer", "rank"], name="unique_ranking_rank_per_answer"),
        ]

class MatrixRow(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="matrix_rows")
    text = models.CharField(max_length=255)
    value = models.CharField(max_length=64, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

class MatrixColumn(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="matrix_columns")
    text = models.CharField(max_length=255)
    value = models.CharField(max_length=64, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

class MatrixAnswerCell(models.Model):
    answer = models.ForeignKey("Answer", on_delete=models.CASCADE, related_name="matrix_cells")
    row = models.ForeignKey(MatrixRow, on_delete=models.CASCADE)
    column = models.ForeignKey(MatrixColumn, on_delete=models.CASCADE)

    def clean(self):
        super().clean()
        if self.answer_id and self.row_id and self.row.question_id != self.answer.question_id:
            raise ValidationError({"row": "Matrix row must belong to the answer question."})
        if self.answer_id and self.column_id and self.column.question_id != self.answer.question_id:
            raise ValidationError({"column": "Matrix column must belong to the answer question."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["answer", "row", "column"],
                name="unique_matrix_cell"
            )
        ]

class Response(models.Model):
    STATUS = (("active","Active"), ("blocked","Blocked"))
    COMPLETE_REASON_CHOICES = (
        ("completed", "Completed normally"),
        ("screened_out", "Screened out"),
    )
    survey = models.ForeignKey(Survey, on_delete=models.PROTECT, related_name="responses")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    
    started_at = models.DateTimeField(auto_now_add=True)
    is_complete = models.BooleanField(default=False)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    client_meta = models.JSONField(default=dict, blank=True)  # user-agent, ip
    status = models.CharField(max_length=10, choices=STATUS, default="active")
    # для идемпотентности
    session_token = models.CharField(max_length=64, unique=True)

    # Для скрининга / досрочного завершения
    screened_out = models.BooleanField(default=False)
    screened_out_at = models.DateTimeField(null=True, blank=True)
    screened_out_reason = models.TextField(blank=True, default="")
    complete_reason = models.CharField(max_length=20, choices=COMPLETE_REASON_CHOICES, blank=True, default="")

    def mark_completed(self):
        self.is_complete = True
        self.finished_at = timezone.now()
        self.complete_reason = "completed"
        self.screened_out = False
        self.screened_out_at = None
        self.save(update_fields=["is_complete", "finished_at", "complete_reason", "screened_out", "screened_out_at"])

    def mark_screened_out(self, reason=""):
        now = timezone.now()
        self.is_complete = True
        self.finished_at = now  
        self.screened_out = True
        self.screened_out_at = now
        self.screened_out_reason = reason
        self.complete_reason = "screened_out"
        self.save(update_fields=[
            "is_complete",
            "finished_at",
            "screened_out",
            "screened_out_at",
            "screened_out_reason",
            "complete_reason",
        ])
    
    class Meta:
        ordering = ["-started_at"]

    def clean(self):
        super().clean()

        if self.screened_out and not self.is_complete:
            raise ValidationError(
                {"screened_out": "screened_out response must also be marked as complete."}
            )

        if self.screened_out and not self.screened_out_at:
            raise ValidationError(
                {"screened_out_at": "screened_out_at is required when screened_out=True."}
            )

        if self.complete_reason == "screened_out" and not self.screened_out:
            raise ValidationError(
                {"complete_reason": "complete_reason='screened_out' requires screened_out=True."}
            )

        if self.complete_reason == "completed" and self.screened_out:
            raise ValidationError(
                {"complete_reason": "completed reason cannot be used for screened_out response."}
            )

        if self.is_complete and not self.finished_at:
            raise ValidationError(
                {"finished_at": "finished_at is required when is_complete=True."}
            )

    def __str__(self):
        return f"Response #{self.id} for survey #{self.survey_id}"

class Answer(models.Model):
    response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    # для single/multi
    selected_options = models.ManyToManyField(Option, blank=True, related_name="answers")
    # для text
    text = models.TextField(blank=True, null=True)
    num = models.FloatField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["response", "question"],
                name="unique_answer_per_response_question",
            )
        ]

class AnalysisReport(models.Model):
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="analysis_reports",
    )
    title = models.CharField(max_length=255)
    config = models.JSONField(default=dict)
    result = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="analysis_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.survey_id})"

class AnalyticResults(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.PROTECT, related_name="produces")
    atype = models.CharField(max_length=20)
    generated_at = models.DateTimeField(auto_now_add=True)
    total_responses = models.PositiveIntegerField(default=0)
    data = models.JSONField(default=dict)

    class Meta:
        unique_together = ("survey", "generated_at")
