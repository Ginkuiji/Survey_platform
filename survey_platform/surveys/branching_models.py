from django.core.exceptions import ValidationError
from django.db import models

from .question_models import Question
from .survey_models import Survey, SurveyPage


class QuestionConditionGroup(models.Model):

    LOGIC_CHOICES = [
        ("all", "All conditions in group must match"),
        ("any", "Any condition in group may match"),
    ]
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="condition_groups"
    )
    title = models.CharField(max_length=255, blank=True, default="")
    logic = models.CharField(max_length=8, choices=LOGIC_CHOICES, default="all")
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["priority", "id"]
        indexes = [
            models.Index(fields=["survey", "priority"]),
            models.Index(fields=["survey", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["survey", "title"], name="unique_condition_group_title_per_survey")
        ]

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
            ("contains_matrix_cell", "Contains matrix cell"),
            ("matrix_row_equals", "Matrix row equals"),
            ("matrix_row_not_equals", "Matrix row not equals"),
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
    matrix_row = models.ForeignKey("MatrixRow", on_delete=models.CASCADE, null=True, blank=True)
    matrix_column = models.ForeignKey("MatrixColumn", on_delete=models.CASCADE, null=True, blank=True)
    # Для группировки нескольких условий в одно правило
    # Например: group_key="screenout_1", group_logic="all"
    group = models.ForeignKey("QuestionConditionGroup", on_delete=models.CASCADE, null=True, blank=True, related_name="conditions")
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

        if self.group_id and self.group.survey_id != survey_id:
            raise ValidationError({"group": "group must belong to the same survey as source_question"})

        if self.option_id and self.option.question_id != self.source_question_id:
            raise ValidationError({"option": "option must belong to source_question"})

        if self.matrix_row_id and self.matrix_row.question_id != self.source_question_id:
            raise ValidationError({"matrix_row": "matrix_row must belong to source_question"})
        
        if self.matrix_column_id and self.matrix_column.question_id != self.source_question_id:
            raise ValidationError({"matrix_column": "matrix_column must belong to source_question"})

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
            
        if self.operator in ("contains_matrix_cell",) and not (self.matrix_row_id and self.matrix_column_id):
            raise ValidationError({"matrix_row": "matrix_row and matrix_column are required for contains_matrix_cell"})

        if self.operator in ("matrix_row_equals", "matrix_row_not_equals") and not (self.matrix_row_id and self.matrix_column_id):
            raise ValidationError({"matrix_row": "matrix_row and matrix_column are required for matrix row operators"})

        if self.action == "terminate" and self.terminate_message and len(self.terminate_message) > 2000:
            raise ValidationError({"terminate_message": "terminate_message is too long"})


    def __str__(self):
        return f"{self.action} from question {self.source_question_id}"
