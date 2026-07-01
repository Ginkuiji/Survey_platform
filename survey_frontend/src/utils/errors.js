const FIELD_LABELS = {
  pages: "страницы",
  questions: "вопросы",
  title: "название",
  description: "описание",
  text: "текст вопроса",
  qtype: "тип вопроса",
  options: "варианты ответа",
  matrix_rows: "строки матрицы",
  matrix_columns: "столбцы матрицы",
  selected_options: "выбранные варианты",
  matrix_cells: "ответы матрицы",
  ranking_items: "ранжирование",
  response_token: "токен ответа",
};

const MESSAGE_TRANSLATIONS = [
  [/^This field may not be blank\.$/i, "заполните поле"],
  [/^This field is required\.$/i, "заполните обязательное поле"],
  [/^This list may not be empty\.$/i, "список не должен быть пустым"],
  [/^A valid integer is required\.$/i, "введите целое число"],
  [/^A valid number is required\.$/i, "введите число"],
  [/^Not a valid string\.$/i, "введите текст"],
  [/^Enter a valid date\.$/i, "введите корректную дату"],
  [/^Duplicate answers for the same question are not allowed$/i, "один и тот же вопрос нельзя отправлять несколько раз"],
  [/^question not in survey$/i, "в ответах есть вопрос, которого нет в этом опросе"],
  [/^invalid or completed token$/i, "прохождение уже завершено или сессия ответа недействительна"],
  [/^Authentication credentials were not provided\.$/i, "для этого действия нужно войти в систему"],
  [/^Session expired$/i, "сессия истекла, войдите снова"],
  [/^API error$/i, "сервер вернул ошибку"],
];

function normalizeOptions(optionsOrFallback) {
  if (typeof optionsOrFallback === "string") {
    return { fallback: optionsOrFallback };
  }

  return {
    fallback: "Произошла ошибка. Попробуйте ещё раз.",
    ...(optionsOrFallback || {}),
  };
}

function truncate(value, maxLength = 90) {
  const text = String(value || "").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}…`;
}

function getQuestionsFromContext(context = {}) {
  const seen = new Set();
  const questions = [];

  const addQuestion = (question, pageIndex = null, questionIndex = null) => {
    if (!question?.id || seen.has(question.id)) return;

    seen.add(question.id);
    questions.push({
      ...question,
      displayNumber: questions.length + 1,
      pageIndex,
      questionIndex,
    });
  };

  (context.questions || []).forEach((question, questionIndex) => {
    addQuestion(question, null, questionIndex);
  });

  (context.pages || []).forEach((page, pageIndex) => {
    (page.questions || []).forEach((question, questionIndex) => {
      addQuestion(question, pageIndex, questionIndex);
    });
  });

  return questions;
}

function buildQuestionLabel(question) {
  if (!question) return "";

  const title = truncate(question.text || question.short_label);
  return title
    ? `Вопрос ${question.displayNumber}: ${title}`
    : `Вопрос ${question.displayNumber}`;
}

function findQuestionById(questionId, context) {
  return getQuestionsFromContext(context).find(question => Number(question.id) === Number(questionId));
}

function getPathContext(path = [], context = {}) {
  const pageEntryIndex = path.findIndex(item => item.key === "pages");
  const questionEntryIndex = path.findIndex(item => item.key === "questions");
  const field = [...path].reverse().find(item => typeof item.key === "string")?.key;
  const parts = [];

  if (pageEntryIndex >= 0 && typeof path[pageEntryIndex + 1]?.index === "number") {
    const pageIndex = path[pageEntryIndex + 1].index;
    parts.push(`страница ${pageIndex + 1}`);
  }

  if (questionEntryIndex >= 0 && typeof path[questionEntryIndex + 1]?.index === "number") {
    const pageIndex = pageEntryIndex >= 0 ? path[pageEntryIndex + 1]?.index : null;
    const questionIndex = path[questionEntryIndex + 1].index;
    const question = pageIndex !== null
      ? context.pages?.[pageIndex]?.questions?.[questionIndex]
      : context.questions?.[questionIndex];
    const label = question?.text
      ? `вопрос ${questionIndex + 1} «${truncate(question.text, 60)}»`
      : `вопрос ${questionIndex + 1}`;
    parts.push(label);
  }

  if (field && !["pages", "questions"].includes(field)) {
    parts.push(FIELD_LABELS[field] || field);
  }

  return parts.join(", ");
}

function translateMessage(message, context = {}) {
  const raw = String(message || "").trim();
  const requiredMatch = raw.match(/^Question\s+(\d+)\s+is required$/i);

  if (requiredMatch) {
    const question = findQuestionById(requiredMatch[1], context);
    if (question) {
      return `обязательный вопрос не заполнен: ${buildQuestionLabel(question)}`;
    }
    return `обязательный вопрос ID ${requiredMatch[1]} не заполнен`;
  }

  const invalidOptionMatch = raw.match(/^Question\s+(\d+)\s+contains invalid selected options$/i);
  if (invalidOptionMatch) {
    const question = findQuestionById(invalidOptionMatch[1], context);
    return question
      ? `в вопросе указан недопустимый вариант ответа: ${buildQuestionLabel(question)}`
      : `в вопросе ID ${invalidOptionMatch[1]} указан недопустимый вариант ответа`;
  }

  const invalidRankingMatch = raw.match(/^Question\s+(\d+)\s+contains invalid ranking options$/i);
  if (invalidRankingMatch) {
    const question = findQuestionById(invalidRankingMatch[1], context);
    return question
      ? `в вопросе указан недопустимый вариант ранжирования: ${buildQuestionLabel(question)}`
      : `в вопросе ID ${invalidRankingMatch[1]} указан недопустимый вариант ранжирования`;
  }

  const fieldMatch = raw.match(/^Question\s+(\d+)\s+\(([^)]+)\)\s+does not allow fields:\s+(.+)$/i);
  if (fieldMatch) {
    const question = findQuestionById(fieldMatch[1], context);
    const fields = fieldMatch[3]
      .split(",")
      .map(field => FIELD_LABELS[field.trim()] || field.trim())
      .join(", ");
    return question
      ? `в вопросе переданы лишние поля (${fields}): ${buildQuestionLabel(question)}`
      : `в вопросе ID ${fieldMatch[1]} переданы лишние поля: ${fields}`;
  }

  const translation = MESSAGE_TRANSLATIONS.find(([pattern]) => pattern.test(raw));
  return translation ? translation[1] : raw;
}

function formatLeafMessage(message, path, context) {
  const translated = translateMessage(message, context);
  const pathContext = getPathContext(path, context);

  if (!pathContext) return translated;

  if (translated === "заполните поле") {
    return `${pathContext}: заполните поле`;
  }

  if (translated === "заполните обязательное поле") {
    return `${pathContext}: заполните обязательное поле`;
  }

  return `${pathContext}: ${translated}`;
}

function flattenMessages(value, context = {}, path = []) {
  if (!value) return [];

  if (typeof value === "string") {
    return [formatLeafMessage(value, path, context)];
  }

  if (Array.isArray(value)) {
    return value.flatMap((item, index) => (
      flattenMessages(item, context, [...path, { index }])
    ));
  }

  if (typeof value === "object") {
    return Object.entries(value).flatMap(([key, nested]) => (
      flattenMessages(nested, context, [...path, { key }])
    ));
  }

  return [formatLeafMessage(String(value), path, context)];
}

function uniqueMessages(messages) {
  return [...new Set(messages.filter(Boolean))];
}

export function getErrorMessage(error, optionsOrFallback = {}) {
  const options = normalizeOptions(optionsOrFallback);
  const rawMessage = error?.message || error;

  if (!rawMessage) return options.fallback;

  if (typeof rawMessage !== "string") {
    const messages = uniqueMessages(flattenMessages(rawMessage, options));
    return messages.join("\n") || options.fallback;
  }

  try {
    const parsed = JSON.parse(rawMessage);
    if (parsed.detail) return translateMessage(parsed.detail, options);
    if (parsed.error) return translateMessage(parsed.error, options);

    const messages = uniqueMessages(flattenMessages(parsed, options));
    return messages.join("\n") || rawMessage || options.fallback;
  } catch {
    return translateMessage(rawMessage, options) || options.fallback;
  }
}
