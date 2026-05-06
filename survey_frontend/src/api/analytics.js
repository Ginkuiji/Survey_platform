import { API_URL, apiFetch } from "./client";

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

export const runCorrespondenceAnalysis = (payload) =>
  apiFetch("/analytics/advanced/correspondence-analysis/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runRegressionAnalysis = (payload) =>
  apiFetch("/analytics/advanced/regression/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runLogisticRegressionAnalysis = (payload) =>
  apiFetch("/analytics/advanced/logistic-regression/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runFactorAnalysis = (payload) =>
  apiFetch("/analytics/advanced/factor-analysis/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runClusterAnalysis = (payload) =>
  apiFetch("/analytics/advanced/cluster-analysis/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runGroupComparisonAnalysis = (payload) =>
  apiFetch("/analytics/advanced/group-comparison/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runTimeAnalysis = (payload) =>
  apiFetch("/analytics/advanced/time-analysis/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runReliabilityAnalysis = (payload) =>
  apiFetch("/analytics/advanced/reliability/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runScaleIndexAnalysis = (payload) =>
  apiFetch("/analytics/advanced/scale-index/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const runMissingAnalysis = (payload) =>
  apiFetch("/analytics/advanced/missing-analysis/", {
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

export const exportAnalyticsPdf = async (payload) => {
  const accessToken = localStorage.getItem("accessToken");

  const res = await fetch(`${API_URL}/analytics/export/pdf/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Ошибка экспорта PDF");
  }

  return res.blob();
};

export const exportAnalyticsCsv = async (payload) => {
  const accessToken = localStorage.getItem("accessToken");

  const res = await fetch(`${API_URL}/analytics/export/csv/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Ошибка экспорта CSV");
  }

  return res.blob();
};

export const exportAnalyticsXlsx = async (payload) => {
  const accessToken = localStorage.getItem("accessToken");

  const res = await fetch(`${API_URL}/analytics/export/xlsx/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Ошибка экспорта XLSX");
  }

  return res.blob();
};
