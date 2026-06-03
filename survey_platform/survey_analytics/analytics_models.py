from django.conf import settings
from django.db import models

from surveys.survey_models import Survey


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
        app_label = "surveys"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.survey_id})"

class AnalyticResults(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.PROTECT, related_name="produces")
    title = models.CharField(max_length=255, blank=True, default='')
    generated_at = models.DateTimeField(auto_now_add=True)
    total_responses = models.PositiveIntegerField(default=0)
    data = models.JSONField(default=dict)

    class Meta:
        app_label = "surveys"
        ordering = ["-generated_at"]
