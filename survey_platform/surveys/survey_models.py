from django.conf import settings
from django.db import models


class Survey(models.Model):
    STATUS = (
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
        ("deleted", "Deleted"),
    )
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
