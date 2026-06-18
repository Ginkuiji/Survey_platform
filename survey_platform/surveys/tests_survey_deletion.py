from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import AnalyticResults, Response, Survey


class SurveyDeletionTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="password",
            role="admin",
        )
        self.client.force_authenticate(self.user)

    def create_survey_with_data(self):
        survey = Survey.objects.create(title="Survey")
        survey.owners.add(self.user)
        response = Response.objects.create(
            survey=survey,
            session_token=f"response-{survey.id}",
        )
        snapshot = AnalyticResults.objects.create(
            survey=survey,
            title="Snapshot",
        )
        return survey, response, snapshot

    def test_delete_without_responses_soft_deletes_survey(self):
        survey, response, snapshot = self.create_survey_with_data()

        result = self.client.delete(
            reverse("admin-survey-detail", args=[survey.id]),
        )

        self.assertEqual(result.status_code, 200)
        survey.refresh_from_db()
        self.assertEqual(survey.status, "deleted")
        self.assertTrue(Response.objects.filter(id=response.id).exists())
        self.assertTrue(AnalyticResults.objects.filter(id=snapshot.id).exists())

    def test_delete_with_responses_removes_survey_and_related_data(self):
        survey, response, snapshot = self.create_survey_with_data()

        result = self.client.delete(
            f"{reverse('admin-survey-detail', args=[survey.id])}?delete_responses=true",
        )

        self.assertEqual(result.status_code, 204)
        self.assertFalse(Survey.objects.filter(id=survey.id).exists())
        self.assertFalse(Response.objects.filter(id=response.id).exists())
        self.assertFalse(AnalyticResults.objects.filter(id=snapshot.id).exists())
