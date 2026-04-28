# surveys/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    AdvancedAnalyticsViewSet,
    AdminSurveyQuestionViewSet,
    AdminSurveyViewSet,
    AnalyticsViewSet,
    SurveyResponseViewSet,
    SurveyViewSet,
    UserViewSet,
    AnalysisReportViewSet,
    AnalyticResultsViewSet,
    AnalyticsExportViewSet,
)

router = DefaultRouter()
router.register(r"surveys", SurveyViewSet, basename="survey")
router.register(r"analytics", AnalyticsViewSet, basename="analytics")
router.register(r"analytics/advanced", AdvancedAnalyticsViewSet, basename="advanced-analytics")
router.register(r"analytics/export", AnalyticsExportViewSet, basename="analytics-export")
router.register(r"admin/surveys", AdminSurveyViewSet, basename="admin-survey")
router.register(r"analytics/reports", AnalysisReportViewSet, basename="analysis-report")
router.register(r"analytics/results", AnalyticResultsViewSet, basename="analytic-results")
urlpatterns = router.urls

survey_responses = SurveyResponseViewSet.as_view({
    "get": "list"
})

survey_response_detail = SurveyResponseViewSet.as_view({
    "get": "retrieve",
    "patch": "partial_update",
})

urlpatterns += [
    path(
        "surveys/<int:survey_id>/responses/",
        survey_responses,
        name="survey-responses",
    ),
    path(
        "surveys/<int:survey_id>/responses/<int:pk>/",
        survey_response_detail,
        name="survey-response-detail",
    ),
]

user_list = UserViewSet.as_view({
    "get": "list"
})

user_detail = UserViewSet.as_view({
    "get": "retrieve",
    "patch": "partial_update"
})

user_me = UserViewSet.as_view({
    "get": "me",
    "patch": "me"
})

urlpatterns += [
    path("users/", user_list, name="user-list"),
    path("users/me/", user_me, name="user-me"),
    path("users/<int:pk>/", user_detail, name="user-detail"),
]

admin_survey_questions = AdminSurveyQuestionViewSet.as_view({
    "post": "bulk"
})

admin_survey_conditions = AdminSurveyViewSet.as_view({
    "post": "bulk_conditions"
})

urlpatterns += [
    path(
        "admin/surveys/<int:pk>/questions/bulk/",
        admin_survey_questions,
        name="admin-survey-questions-bulk",
    ),
    path(
        "admin/surveys/<int:pk>/conditions/bulk/",
        admin_survey_conditions,
        name="admin-survey-conditions-bulk",
    ),
]
