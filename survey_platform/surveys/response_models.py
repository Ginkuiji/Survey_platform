from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .question_models import MatrixColumn, MatrixRow, Option, Question
from .survey_models import Survey


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
