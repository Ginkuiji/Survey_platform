from django.contrib import admin
from .models import Survey, Question, Option, Response, Answer, AnalyticResults, AnalysisReport

admin.site.register([Survey, Question, Option, Response, Answer, AnalyticResults, AnalysisReport])

# Register your models here.
