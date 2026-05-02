const QUESTION_TYPE_LABELS = {
  single: "Одиночный выбор",
  multi: "Множественный выбор",
  dropdown: "Выпадающий список",
  yesno: "Да/Нет",
  scale: "Шкала",
  number: "Число",
  ranking: "Ранжирование",
  matrix_single: "Матрица: один выбор",
  matrix_multi: "Матрица: много выборов",
  text: "Текст",
  date: "Дата",
};

export function getAllSurveyQuestions(survey) {
  const byId = new Map();

  (survey?.questions || []).forEach((question) => {
    byId.set(question.id, question);
  });

  (survey?.pages || []).forEach((page) => {
    (page.questions || []).forEach((question) => {
      byId.set(question.id, question);
    });
  });

  return Array.from(byId.values());
}

export function getQuestionTypeLabel(qtype) {
  return QUESTION_TYPE_LABELS[qtype] || qtype;
}

export function isQuestionSupportedForAnalysis(question, analysisType, role = "variable") {
  if (!question) return false;

  if (analysisType === "correlation") {
    return ["scale", "number", "yesno", "single", "dropdown", "ranking", "matrix_single"].includes(question.qtype);
  }

  if (analysisType === "crosstab" || analysisType === "chi_square") {
    return ["single", "dropdown", "yesno"].includes(question.qtype);
  }

  if (analysisType === "regression") {
    if (role === "target") {
      return ["scale", "number"].includes(question.qtype);
    }
    return ["scale", "number", "yesno", "single", "dropdown", "multi", "ranking", "matrix_single", "matrix_multi"].includes(question.qtype);
  }

  if (analysisType === "factor_analysis") {
    return ["scale", "number", "yesno", "single", "dropdown", "ranking", "matrix_single"].includes(question.qtype);
  }

  if (analysisType === "cluster_analysis") {
    return ["scale", "number", "yesno", "single", "dropdown", "ranking", "matrix_single", "matrix_multi"].includes(question.qtype);
  }

  if (analysisType === "group_comparison") {
    if (role === "group") {
      return ["single", "dropdown", "yesno"].includes(question.qtype);
    }
    if (role === "value") {
      return ["scale", "number", "yesno", "single", "dropdown"].includes(question.qtype);
    }
    return false;
  }

  return false;
}

export function getDefaultVariableSpec(question, analysisType, role = "variable") {
  if (!isQuestionSupportedForAnalysis(question, analysisType, role)) {
    return null;
  }

  if (["number", "scale"].includes(question.qtype)) {
    return { question_id: question.id, encoding: "numeric", measure: "interval" };
  }

  if (question.qtype === "yesno") {
    return { question_id: question.id, encoding: "binary", measure: "binary" };
  }

  if (["single", "dropdown"].includes(question.qtype)) {
    if (analysisType === "group_comparison" && role === "group") {
      return { question_id: question.id, encoding: "ordinal", measure: "nominal" };
    }

    if (analysisType === "group_comparison" && role === "value") {
      return { question_id: question.id, encoding: "ordinal", measure: "ordinal" };
    }

    if (analysisType === "correlation" || analysisType === "factor_analysis" || analysisType === "cluster_analysis") {
      return { question_id: question.id, encoding: "ordinal", measure: "ordinal" };
    }

    if (analysisType === "crosstab" || analysisType === "chi_square") {
      return { question_id: question.id, encoding: "ordinal", measure: "nominal" };
    }

    if (analysisType === "regression" && role === "feature") {
      return { question_id: question.id, encoding: "one_hot", measure: "nominal" };
    }
  }

  if (question.qtype === "multi" && analysisType === "regression" && role === "feature") {
    return { question_id: question.id, encoding: "one_hot", measure: "nominal" };
  }

  if (question.qtype === "ranking") {
    return { question_id: question.id, encoding: "rank", measure: "ordinal" };
  }

  if (question.qtype === "matrix_single") {
    return { question_id: question.id, encoding: "matrix_ordinal", measure: "ordinal" };
  }

  if (question.qtype === "matrix_multi" && analysisType === "regression" && role === "feature") {
    return { question_id: question.id, encoding: "matrix_multi_binary", measure: "binary" };
  }

  if (question.qtype === "matrix_multi" && analysisType === "cluster_analysis") {
    return { question_id: question.id, encoding: "matrix_multi_binary", measure: "binary" };
  }

  return null;
}

function getQuestion(questionsById, questionId, roleLabel) {
  const question = questionsById.get(Number(questionId));
  if (!question) {
    throw new Error(`Не выбран вопрос для поля "${roleLabel}".`);
  }
  return question;
}

function getSpec(question, analysisType, role, roleLabel) {
  const spec = getDefaultVariableSpec(question, analysisType, role);
  if (!spec) {
    throw new Error(`Вопрос "${question.text}" не поддерживается для поля "${roleLabel}".`);
  }
  return spec;
}

export function buildSectionPayload(surveyId, section, questionsById) {
  if (section.type === "correlation") {
    if ((section.questionIds || []).length < 2) {
      throw new Error("Для корреляционного анализа выберите минимум два вопроса.");
    }

    return {
      survey_id: Number(surveyId),
      method: section.method || "pearson",
      variables: section.questionIds.map((questionId) => {
        const question = getQuestion(questionsById, questionId, "Переменные");
        return getSpec(question, "correlation", "variable", "Переменные");
      }),
    };
  }

  if (section.type === "crosstab" || section.type === "chi_square") {
    if (!section.rowQuestionId || !section.columnQuestionId) {
      throw new Error("Выберите вопросы для строк и столбцов.");
    }
    if (Number(section.rowQuestionId) === Number(section.columnQuestionId)) {
      throw new Error("Вопросы для строк и столбцов должны отличаться.");
    }

    const rowQuestion = getQuestion(questionsById, section.rowQuestionId, "Строки");
    const columnQuestion = getQuestion(questionsById, section.columnQuestionId, "Столбцы");

    return {
      survey_id: Number(surveyId),
      row: getSpec(rowQuestion, section.type, "row", "Строки"),
      column: getSpec(columnQuestion, section.type, "column", "Столбцы"),
    };
  }

  if (section.type === "regression") {
    if (!section.targetQuestionId) {
      throw new Error("Выберите целевой вопрос для регрессии.");
    }
    if ((section.featureQuestionIds || []).length < 1) {
      throw new Error("Для регрессии выберите минимум один фактор.");
    }
    if ((section.featureQuestionIds || []).some((questionId) => Number(questionId) === Number(section.targetQuestionId))) {
      throw new Error("Целевой вопрос не должен быть среди факторов.");
    }

    const targetQuestion = getQuestion(questionsById, section.targetQuestionId, "Целевая переменная");

    return {
      survey_id: Number(surveyId),
      target: getSpec(targetQuestion, "regression", "target", "Целевая переменная"),
      features: section.featureQuestionIds.map((questionId) => {
        const question = getQuestion(questionsById, questionId, "Факторы");
        return getSpec(question, "regression", "feature", "Факторы");
      }),
      include_intercept: section.include_intercept ?? true,
    };
  }

  if (section.type === "factor_analysis") {
    if ((section.questionIds || []).length < 3) {
      throw new Error("Для факторного анализа выберите минимум три вопроса.");
    }

    return {
      survey_id: Number(surveyId),
      variables: section.questionIds.map((questionId) => {
        const question = getQuestion(questionsById, questionId, "Переменные");
        return getSpec(question, "factor_analysis", "variable", "Переменные");
      }),
      n_factors: section.n_factors || 2,
      rotation: section.rotation || "varimax",
      standardize: section.standardize ?? true,
    };
  }

  if (section.type === "cluster_analysis") {
    if ((section.questionIds || []).length < 2) {
      throw new Error("Для кластерного анализа выберите минимум две переменные.");
    }

    return {
      survey_id: Number(surveyId),
      variables: section.questionIds.map((questionId) => {
        const question = getQuestion(questionsById, questionId, "Переменные");
        return getSpec(question, "cluster_analysis", "variable", "Переменные");
      }),
      n_clusters: section.n_clusters || 3,
      standardize: section.standardize ?? true,
      max_iter: section.max_iter || 300,
    };
  }

  if (section.type === "group_comparison") {
    if (!section.groupQuestionId || !section.valueQuestionId) {
      throw new Error("Выберите группирующий вопрос и анализируемый показатель.");
    }

    if (Number(section.groupQuestionId) === Number(section.valueQuestionId)) {
      throw new Error("Группирующий вопрос и показатель должны отличаться.");
    }

    const groupQuestion = getQuestion(questionsById, section.groupQuestionId, "Группирующая переменная");
    const valueQuestion = getQuestion(questionsById, section.valueQuestionId, "Показатель");

    return {
      survey_id: Number(surveyId),
      group: getSpec(groupQuestion, "group_comparison", "group", "Группирующая переменная"),
      value: getSpec(valueQuestion, "group_comparison", "value", "Показатель"),
      method: section.method || "anova",
      alpha: section.alpha ?? 0.05,
    };
  }

  throw new Error("Неизвестный тип аналитического блока.");
}
