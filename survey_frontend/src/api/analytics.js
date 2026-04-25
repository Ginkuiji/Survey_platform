import { apiFetch } from "./client";

export const fetchQuestionAnalytics = (questionId) =>
  apiFetch(`/analytics/distribution/?question_id=${questionId}`);

export const fetchSurveyAnalytics = (surveyId) =>
  apiFetch(`/analytics/survey/?survey_id=${surveyId}`);

export const fetchSurveyResponses = (surveyId) =>
  apiFetch(`/surveys/${surveyId}/responses/`);
