const choiceTypes = ["single", "dropdown", "yesno"];
const multiChoiceTypes = ["multi"];
const textTypes = ["text", "date"];
const numericTypes = ["scale", "number"];
const matrixTypes = ["matrix_single", "matrix_multi"];

export const CONDITION_ACTIONS = [
  { value: "show_question", label: "Показать вопрос" },
  { value: "show_page", label: "Показать страницу" },
  { value: "jump_to_page", label: "Перейти на страницу" },
  { value: "terminate", label: "Завершить опрос" },
];

export const CONDITION_OPERATORS = [
  { value: "equals", label: "равно" },
  { value: "not_equals", label: "не равно" },
  { value: "contains_option", label: "содержит вариант" },
  { value: "gt", label: ">" },
  { value: "lt", label: "<" },
  { value: "gte", label: ">=" },
  { value: "lte", label: "<=" },
  { value: "is_answered", label: "заполнен" },
  { value: "not_answered", label: "не заполнен" },
];

export function createEmptyCondition(priority = 0) {
  return {
    id: `condition-new-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    source_question: "",
    question: "",
    page: "",
    action: "show_question",
    target_page: "",
    operator: "equals",
    value_text: "",
    value_number: "",
    option: "",
    group_key: "",
    group_logic: "all",
    priority,
    is_active: true,
    terminate_message: "",
  };
}

export function getSurveyQuestions(pages = []) {
  return pages.flatMap((page, pageIndex) =>
    (page.questions || []).map((question, questionIndex) => ({
      ...question,
      page_id: page.id,
      page_title: page.title,
      pageIndex,
      questionIndex,
    }))
  );
}

export function getSurveyPages(pages = []) {
  return pages.map((page, pageIndex) => ({
    ...page,
    pageIndex,
  }));
}

export function getConditionPaths(condition, pages = []) {
  const questions = getSurveyQuestions(pages);
  const pageList = getSurveyPages(pages);
  const sourceQuestion = questions.find(q => q.id === condition.source_question);
  const targetQuestion = questions.find(q => q.id === condition.question);
  const page = pageList.find(item => item.id === condition.page);
  const targetPage = pageList.find(item => item.id === condition.target_page);
  const optionIndex = sourceQuestion?.options?.findIndex(option => option.id === condition.option);

  return {
    source: sourceQuestion
      ? { pageIndex: sourceQuestion.pageIndex, questionIndex: sourceQuestion.questionIndex }
      : null,
    question: targetQuestion
      ? { pageIndex: targetQuestion.pageIndex, questionIndex: targetQuestion.questionIndex }
      : null,
    page: page ? { pageIndex: page.pageIndex } : null,
    targetPage: targetPage ? { pageIndex: targetPage.pageIndex } : null,
    optionIndex: optionIndex >= 0 ? optionIndex : null,
  };
}

function questionByPath(pages, path) {
  if (!path) return null;
  return pages[path.pageIndex]?.questions?.[path.questionIndex] || null;
}

function pageByPath(pages, path) {
  if (!path) return null;
  return pages[path.pageIndex] || null;
}

function hasNumericId(value) {
  return typeof value === "number";
}

function cleanId(value) {
  return value === "" || value === null || value === undefined ? null : value;
}

export function buildConditionPayload(condition, originalPages, savedPages) {
  const paths = getConditionPaths(condition, originalPages);
  const sourceQuestion = questionByPath(savedPages, paths.source);
  if (!sourceQuestion || !hasNumericId(sourceQuestion.id)) return null;

  const targetQuestion = questionByPath(savedPages, paths.question);
  const page = pageByPath(savedPages, paths.page);
  const targetPage = pageByPath(savedPages, paths.targetPage);
  const option = paths.optionIndex !== null
    ? sourceQuestion.options?.[paths.optionIndex]
    : null;

  const payload = {
    source_question: sourceQuestion.id,
    question: null,
    page: null,
    action: condition.action,
    target_page: null,
    operator: condition.operator,
    value_text: "",
    value_number: null,
    option: null,
    group_key: condition.group_key || "",
    group_logic: condition.group_logic || "all",
    priority: Number(condition.priority || 0),
    is_active: condition.is_active ?? true,
    terminate_message: condition.action === "terminate" ? (condition.terminate_message || "") : "",
  };

  if (condition.action === "show_question") {
    if (!targetQuestion || !hasNumericId(targetQuestion.id)) return null;
    payload.question = targetQuestion.id;
  }
  if (condition.action === "show_page") {
    if (!page || !hasNumericId(page.id)) return null;
    payload.page = page.id;
  }
  if (condition.action === "jump_to_page") {
    if (!targetPage || !hasNumericId(targetPage.id)) return null;
    payload.target_page = targetPage.id;
  }

  if (condition.operator === "contains_option") {
    if (!option || !hasNumericId(option.id)) return null;
    payload.option = option.id;
    return payload;
  }

  if (condition.operator === "equals" || condition.operator === "not_equals") {
    if ([...choiceTypes, ...multiChoiceTypes, "ranking"].includes(sourceQuestion.qtype) && !option) {
      return null;
    }
    if (option && hasNumericId(option.id)) {
      payload.option = option.id;
    } else if (condition.value_number !== "" && condition.value_number !== null && condition.value_number !== undefined) {
      payload.value_number = Number(condition.value_number);
    } else {
      payload.value_text = condition.value_text || "";
    }
  }

  if (["gt", "lt", "gte", "lte"].includes(condition.operator)) {
    if (condition.value_number === "" || condition.value_number === null || condition.value_number === undefined) {
      return null;
    }
    payload.value_number = Number(condition.value_number);
  }

  return payload;
}

export function mapServerConditionsToEditor(conditions = []) {
  return conditions.map((condition, index) => ({
    id: condition.id,
    source_question: cleanId(condition.source_question) || "",
    question: cleanId(condition.question) || "",
    page: cleanId(condition.page) || "",
    action: condition.action || "show_question",
    target_page: cleanId(condition.target_page) || "",
    operator: condition.operator || "equals",
    value_text: condition.value_text || "",
    value_number: condition.value_number ?? "",
    option: cleanId(condition.option) || "",
    group_key: condition.group_key || "",
    group_logic: condition.group_logic || "all",
    priority: condition.priority ?? index,
    is_active: condition.is_active ?? true,
    terminate_message: condition.terminate_message || "",
  }));
}

export function normalizeEditorConditions(conditions = []) {
  return conditions.map((condition, index) => ({
    source_question: condition.source_question || "",
    question: condition.question || "",
    page: condition.page || "",
    action: condition.action || "show_question",
    target_page: condition.target_page || "",
    operator: condition.operator || "equals",
    value_text: condition.value_text || "",
    value_number: condition.value_number ?? "",
    option: condition.option || "",
    group_key: condition.group_key || "",
    group_logic: condition.group_logic || "all",
    priority: condition.priority ?? index,
    is_active: condition.is_active ?? true,
    terminate_message: condition.terminate_message || "",
  }));
}

function answerHasValue(question, answer) {
  if (!answer) return false;
  if ([...choiceTypes, ...multiChoiceTypes].includes(question.qtype)) {
    return Boolean(answer.selected_options?.length);
  }
  if (textTypes.includes(question.qtype)) {
    return Boolean((answer.text || "").trim());
  }
  if (numericTypes.includes(question.qtype)) {
    return answer.num !== null && answer.num !== undefined;
  }
  if (matrixTypes.includes(question.qtype)) {
    return Boolean(answer.matrix_cells?.length);
  }
  if (question.qtype === "ranking") {
    return Boolean(answer.ranking_items?.length);
  }
  return false;
}

function extractAnswerValue(question, answer) {
  if (!answer) return null;
  if (choiceTypes.includes(question.qtype)) {
    return answer.selected_options?.[0] ?? null;
  }
  if (multiChoiceTypes.includes(question.qtype)) {
    return answer.selected_options || [];
  }
  if (textTypes.includes(question.qtype)) {
    return (answer.text || "").trim();
  }
  if (numericTypes.includes(question.qtype)) {
    return answer.num;
  }
  if (matrixTypes.includes(question.qtype)) {
    return answer.matrix_cells || [];
  }
  if (question.qtype === "ranking") {
    return answer.ranking_items || [];
  }
  return null;
}

export function conditionMatches(condition, answers, questionsById) {
  const sourceQuestion = questionsById[condition.source_question];
  const answer = answers[condition.source_question];
  if (!sourceQuestion) return false;

  if (condition.operator === "is_answered") {
    return answerHasValue(sourceQuestion, answer);
  }
  if (condition.operator === "not_answered") {
    return !answerHasValue(sourceQuestion, answer);
  }

  const value = extractAnswerValue(sourceQuestion, answer);

  if (condition.operator === "contains_option") {
    if (!condition.option) return false;
    if (choiceTypes.includes(sourceQuestion.qtype)) return value === condition.option;
    if (multiChoiceTypes.includes(sourceQuestion.qtype)) return value.includes(condition.option);
    return false;
  }

  if (condition.operator === "equals" || condition.operator === "not_equals") {
    let expected = condition.value_text || "";
    if (condition.option) expected = condition.option;
    if (condition.value_number !== null && condition.value_number !== undefined && condition.value_number !== "") {
      expected = Number(condition.value_number);
    }
    const result = value === expected;
    return condition.operator === "equals" ? result : !result;
  }

  if (["gt", "lt", "gte", "lte"].includes(condition.operator)) {
    if (value === null || value === undefined || condition.value_number === null || condition.value_number === undefined) {
      return false;
    }
    const current = Number(value);
    const expected = Number(condition.value_number);
    if (Number.isNaN(current) || Number.isNaN(expected)) return false;
    if (condition.operator === "gt") return current > expected;
    if (condition.operator === "lt") return current < expected;
    if (condition.operator === "gte") return current >= expected;
    if (condition.operator === "lte") return current <= expected;
  }

  return false;
}

export function getMatchedConditions(conditions = [], answers = {}, questionsById = {}) {
  const groups = new Map();
  conditions
    .filter(condition => condition.is_active !== false)
    .forEach((condition, index) => {
      const key = condition.group_key || `__condition_${condition.id || index}`;
      groups.set(key, [...(groups.get(key) || []), condition]);
    });

  const matched = [];
  groups.forEach(groupConditions => {
    const results = groupConditions.map(condition => ({
      condition,
      matches: conditionMatches(condition, answers, questionsById),
    }));

    if (groupConditions[0]?.group_logic === "any") {
      matched.push(...results.filter(item => item.matches).map(item => item.condition));
    } else if (results.every(item => item.matches)) {
      matched.push(...groupConditions);
    }
  });

  return matched;
}

export function getVisiblePages(pages = [], conditions = [], answers = {}) {
  const questions = getSurveyQuestions(pages);
  const questionsById = Object.fromEntries(questions.map(question => [question.id, question]));
  const matched = getMatchedConditions(conditions, answers, questionsById);
  const matchedIds = new Set(matched.map(condition => condition.id));

  const pageShowConditions = conditions.filter(condition => condition.action === "show_page");
  const questionShowConditions = conditions.filter(condition => condition.action === "show_question");

  return pages
    .filter(page => {
      const incoming = pageShowConditions.filter(condition => condition.page === page.id);
      return incoming.length === 0 || incoming.some(condition => matchedIds.has(condition.id));
    })
    .map(page => ({
      ...page,
      questions: (page.questions || []).filter(question => {
        const incoming = questionShowConditions.filter(condition => condition.question === question.id);
        return incoming.length === 0 || incoming.some(condition => matchedIds.has(condition.id));
      }),
    }));
}

export function getJumpTargetPageId(conditions = [], answers = {}, questionsById = {}) {
  const matched = getMatchedConditions(conditions, answers, questionsById);
  return matched.find(condition => condition.action === "jump_to_page" && condition.target_page)?.target_page || null;
}

export function getTerminateCondition(conditions = [], answers = {}, questionsById = {}) {
  const matched = getMatchedConditions(conditions, answers, questionsById);
  return matched.find(condition => condition.action === "terminate") || null;
}
