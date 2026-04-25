from django.contrib import admin
from .models import Survey, Question, Option, Response, Answer, AnalyticResults

admin.site.register([Survey, Question, Option, Response, Answer, AnalyticResults])

# Register your models here.
