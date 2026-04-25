export const QuestionType = {
  TEXT: "text",
  SINGLE: "single",
  MULTI: "multi",
  NUMBER: "number",
  SCALE: "scale",
  DROPDOWN: "dropdown",
  YESNO: "yesno",
  DATE: "date",
  MATRIX_SINGLE: "matrix_single",
  MATRIX_MULTI: "matrix_multi",
  RANKING: "ranking"
};

export const QUESTION_TYPE_OPTIONS = [
  { value: QuestionType.SINGLE, label: "Одиночный выбор" },
  { value: QuestionType.MULTI, label: "Множественный выбор" },
  { value: QuestionType.DROPDOWN, label: "Выпадающий список" },
  { value: QuestionType.YESNO, label: "Да/Нет" },
  { value: QuestionType.NUMBER, label: "Число" },
  { value: QuestionType.DATE, label: "Дата" },
  { value: QuestionType.SCALE, label: "Шкала" },
  { value: QuestionType.TEXT, label: "Текст" },
  { value: QuestionType.MATRIX_SINGLE, label: "Матрица: один выбор" },
  { value: QuestionType.MATRIX_MULTI, label: "Матрица: много выборов" },
  { value: QuestionType.RANKING, label: "Ранжирование" }
];

export function createEmptyQuestion(qtype = QuestionType.SINGLE) {
  const base = {
    id: `question-new-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    text: "",
    qtype,
    required: true,
    qsettings: {},
    randomize_options: false,
    options: [],
    matrix_rows: [],
    matrix_columns: []
  };

  if (qtype === QuestionType.SCALE) {
    return {
      ...base,
      qsettings: { min: 1, max: 5, step: 1 }
    };
  }

  if (qtype === QuestionType.DROPDOWN) {
    return {
      ...base,
      qsettings: { placeholder: "Выберите вариант" }
    };
  }

  if (qtype === QuestionType.YESNO) {
    return {
      ...base,
      options: [
        { id: `yes-${Date.now()}`, text: "Да", value: "yes", order: 0 },
        { id: `no-${Date.now()}`, text: "Нет", value: "no", order: 1 }
      ]
    };
  }

  if (qtype === QuestionType.NUMBER) {
    return {
      ...base,
      qsettings: { min: "", max: "", integer: false }
    };
  }

  if (qtype === QuestionType.DATE) {
    return {
      ...base,
      qsettings: { min: "", max: "" }
    };
  }

  if (qtype === QuestionType.MATRIX_SINGLE || qtype === QuestionType.MATRIX_MULTI) {
    return {
      ...base,
      matrix_rows: [
        { id: `row-${Date.now()}-1`, text: "Строка 1", value: "row_1", order: 0 },
        { id: `row-${Date.now()}-2`, text: "Строка 2", value: "row_2", order: 1 }
      ],
      matrix_columns: [
        { id: `column-${Date.now()}-1`, text: "Вариант 1", value: "column_1", order: 0 },
        { id: `column-${Date.now()}-2`, text: "Вариант 2", value: "column_2", order: 1 }
      ]
    };
  }

  if (qtype === QuestionType.RANKING) {
    return {
      ...base,
      qsettings: { full_ranking: true },
      options: [
        { id: `ranking-${Date.now()}-1`, text: "Вариант 1", value: "option_1", order: 0 },
        { id: `ranking-${Date.now()}-2`, text: "Вариант 2", value: "option_2", order: 1 },
        { id: `ranking-${Date.now()}-3`, text: "Вариант 3", value: "option_3", order: 2 }
      ]
    };
  }

  return base;
}

export function createEmptySurvey() {
  return {
    id: null,
    title: "",
    description: "",
    questions: []
  };
}
