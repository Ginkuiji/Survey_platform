import { apiFetch } from "./client";

export const fetchAdminSurveyById = (id) =>
  apiFetch(`/admin/surveys/${id}/`);

// список опросов
export const fetchSurveys = () =>
  apiFetch("/surveys/");

export const fetchAdminSurveys = () =>
  apiFetch("/admin/surveys/");

// один опрос (для прохождения и аналитики)
export const fetchSurveyById = (id) =>
  apiFetch(`/surveys/${id}/`);

// ===== ПРОХОЖДЕНИЕ ОПРОСА =====

// старт сессии ответа
export const startSurvey = (surveyId) =>
  apiFetch(`/surveys/${surveyId}/start/`, {
    method: "POST"
  });

// отправка ответов
export const submitSurvey = (payload) =>
  apiFetch("/surveys/submit/", {
    method: "POST",
    body: JSON.stringify(payload)
  });

// ===== АДМИН =====

export const createSurvey = (data) =>
  apiFetch("/admin/surveys/", {
    method: "POST",
    body: JSON.stringify(data)
  });

export const updateSurvey = (id, data) =>
  apiFetch(`/admin/surveys/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data)
  });

const choiceTypes = ["single", "multi", "dropdown", "yesno", "ranking"];
const matrixTypes = ["matrix_single", "matrix_multi"];

function mapOptions(q) {
  return choiceTypes.includes(q.qtype)
    ? (q.options || []).map((o, oIndex) => ({
        text: o.text,
        value: o.value ?? "",
        order: oIndex,
      }))
    : [];
}

function mapMatrixItems(items = []) {
  return items.map((item, index) => ({
    text: item.text,
    value: item.value ?? "",
    order: index,
  }));
}

function mapQuestionPayload(q, index) {
  const isMatrix = matrixTypes.includes(q.qtype);

  return {
    text: q.text,
    qtype: q.qtype,
    required: q.required ?? true,
    qsettings: q.qsettings ?? {},
    order: index,
    randomize_options: q.randomize_options ?? false,
    options: mapOptions(q),
    matrix_rows: isMatrix ? mapMatrixItems(q.matrix_rows || []) : [],
    matrix_columns: isMatrix ? mapMatrixItems(q.matrix_columns || []) : [],
  };
}

export async function saveSurveyQuestions(surveyId, questions) {
  const payload = {
    questions: questions.map((q, qIndex) => mapQuestionPayload(q, qIndex))
  };

  return apiFetch(`/admin/surveys/${surveyId}/questions/bulk/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

  // const res = await fetch(
  //   `http://127.0.0.1:8000/api/admin/surveys/${surveyId}/questions/bulk/`,
  //   {
  //     method: "POST",
  //     headers: getAuthHeaders(),
  //     body: JSON.stringify(payload)
  //   }
  // );

  // if (!res.ok) {
  //   throw new Error("Ошибка сохранения вопросов");
  // }

  // return res.json();
}

export async function saveSurveyPages(surveyId, pages) {
  const payload = {
    pages: pages.map((page, pageIndex) => ({
      title: page.title ?? "",
      description: page.description ?? "",
      order: pageIndex,
      randomize_questions: page.randomize_questions ?? false,
      questions: (page.questions || []).map((q, qIndex) => mapQuestionPayload(q, qIndex))
    }))
  };

  return apiFetch(`/admin/surveys/${surveyId}/pages/bulk/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function saveSurveyConditions(surveyId, conditions) {
  return apiFetch(`/admin/surveys/${surveyId}/conditions/bulk/`, {
    method: "POST",
    body: JSON.stringify({ conditions }),
  });
}


/* -------- ответы по опросу -------- */
export async function fetchSurveyResponses(surveyId) {
  return apiFetch(`/surveys/${surveyId}/responses/`);
  // const res = await fetch(
  //   `${API_URL}/surveys/${surveyId}/responses/`,
  //   {
  //     method: "GET",
  //     headers: {
  //       "Content-Type": "application/json"
  //     }
  //   }
  // );

  // if (!res.ok) {
  //   throw new Error("Ошибка загрузки ответов опроса");
  // }

  // return res.json();
}

export async function fetchSurveyResponseById(surveyId, responseId) {
  return apiFetch(`/surveys/${surveyId}/responses/${responseId}/`);
}

export async function updateSurveyResponseStatus(surveyId, responseId, status) {
  return apiFetch(`/surveys/${surveyId}/responses/${responseId}/`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

