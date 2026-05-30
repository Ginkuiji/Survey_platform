from django.db import models

from .survey_models import Survey, SurveyPage


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

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    value = models.CharField(max_length=64, blank=True)  # код варианта
    order = models.PositiveIntegerField(default=0)

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
