import { apiFetch } from "./client";

export const fetchQuestionAnalytics = (questionId) =>
  apiFetch(`/analytics/distribution/?question_id=${questionId}`);

export const fetchSurveyAnalytics = (surveyId) =>
  apiFetch(`/analytics/survey/?survey_id=${surveyId}`);

export const fetchSurveyResponses = (surveyId) =>
  apiFetch(`/surveys/${surveyId}/responses/`);

export const runCorrelationAnalysis = (payload) =>
  apiFetch("/analytics/advanced/correlation/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runCrosstabAnalysis = (payload) =>
  apiFetch("/analytics/advanced/crosstab/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runChiSquareAnalysis = (payload) =>
  apiFetch("/analytics/advanced/chi-square/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runRegressionAnalysis = (payload) =>
  apiFetch("/analytics/advanced/regression/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const fetchAnalysisReports = () =>
  apiFetch("/analytics/reports/");

export const fetchAnalysisReportById = (id) =>
  apiFetch(`/analytics/reports/${id}/`);

export const createAnalysisReport = (payload) =>
  apiFetch("/analytics/reports/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateAnalysisReport = (id, payload) =>
  apiFetch(`/analytics/reports/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const deleteAnalysisReport = (id) =>
  apiFetch(`/analytics/reports/${id}/`, {
    method: "DELETE",
  });

export const fetchAnalyticResults = (surveyId) =>
  apiFetch(`/analytics/results/?survey_id=${surveyId}`);

export const fetchAnalyticResultById = (id) =>
  apiFetch(`/analytics/results/${id}/`);

export const createAnalyticResult = (payload) =>
  apiFetch(`/analytics/results/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const deleteAnalyticResults = (id) =>
  apiFetch(`/analytics/results/${id}/`, {
    method: "DELETE",
  });
