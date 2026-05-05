import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Container,
  FormControl,
  FormControlLabel,
  InputLabel,
  ListItemText,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";

import { fetchAdminSurveyById } from "../../api/surveys";
import {
  createAnalysisReport,
  runChiSquareAnalysis,
  runClusterAnalysis,
  runCorrespondenceAnalysis,
  runCorrelationAnalysis,
  runCrosstabAnalysis,
  runFactorAnalysis,
  runGroupComparisonAnalysis,
  runLogisticRegressionAnalysis,
  runReliabilityAnalysis,
  runRegressionAnalysis,
} from "../../api/analytics";
import {
  buildSectionPayload,
  getAllSurveyQuestions,
  getQuestionTypeLabel,
  isQuestionSupportedForAnalysis,
} from "../../utils/advancedAnalytics";

const ANALYSIS_TYPES = [
  { value: "correlation", label: "Корреляционный анализ" },
  { value: "crosstab", label: "Таблица сопряжённости" },
  { value: "chi_square", label: "χ²-критерий" },
  { value: "correspondence_analysis", label: "Анализ соответствий" },
  { value: "regression", label: "Линейная регрессия" },
  { value: "logistic_regression", label: "Логистическая регрессия" },
  { value: "factor_analysis", label: "Факторный анализ" },
  { value: "cluster_analysis", label: "Кластерный анализ" },
  { value: "group_comparison", label: "Сравнение групп" },
  { value: "reliability_analysis", label: "Надёжность шкалы" },
];

const API_BY_TYPE = {
  correlation: runCorrelationAnalysis,
  crosstab: runCrosstabAnalysis,
  chi_square: runChiSquareAnalysis,
  correspondence_analysis: runCorrespondenceAnalysis,
  regression: runRegressionAnalysis,
  logistic_regression: runLogisticRegressionAnalysis,
  factor_analysis: runFactorAnalysis,
  cluster_analysis: runClusterAnalysis,
  group_comparison: runGroupComparisonAnalysis,
  reliability_analysis: runReliabilityAnalysis,
};

function createSection(type) {
  const id = crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`;

  if (type === "correlation") {
    return { id, type, title: "Корреляционный анализ", method: "pearson", questionIds: [] };
  }

  if (type === "crosstab") {
    return { id, type, title: "Таблица сопряжённости", rowQuestionId: "", columnQuestionId: "" };
  }

  if (type === "chi_square") {
    return { id, type, title: "χ²-критерий", rowQuestionId: "", columnQuestionId: "" };
  }

  if (type === "correspondence_analysis") {
    return {
      id,
      type,
      title: "Анализ соответствий",
      rowQuestionId: "",
      columnQuestionId: "",
      n_dimensions: 2,
    };
  }

  if (type === "factor_analysis") {
    return {
      id,
      type,
      title: "Факторный анализ",
      questionIds: [],
      n_factors: 2,
      rotation: "varimax",
      standardize: true,
    };
  }

  if (type === "logistic_regression") {
    return {
      id,
      type,
      title: "Логистическая регрессия",
      targetQuestionId: "",
      featureQuestionIds: [],
      include_intercept: true,
      threshold: 0.5,
      max_iter: 1000,
      learning_rate: 0.1,
      regularization: "l2",
      lambda_: 0.01,
    };
  }

  if (type === "cluster_analysis") {
    return {
      id,
      type,
      title: "Кластерный анализ",
      questionIds: [],
      profileQuestionIds: [],
      n_clusters: 3,
      standardize: true,
      max_iter: 300,
      max_profile_features: 5,
    };
  }

  if (type === "group_comparison") {
    return {
      id,
      type,
      title: "Сравнение групп",
      groupQuestionId: "",
      valueQuestionId: "",
      method: "anova",
      alpha: 0.05,
      post_hoc: false,
      post_hoc_method: "auto",
      p_adjust: "bonferroni",
    };
  }

  if (type === "reliability_analysis") {
    return {
      id,
      type,
      title: "Надёжность шкалы",
      questionIds: [],
      standardize: false,
    };
  }

  return {
    id,
    type: "regression",
    title: "Линейная регрессия",
    targetQuestionId: "",
    featureQuestionIds: [],
    include_intercept: true,
  };
}

function getErrorMessage(error) {
  try {
    const data = JSON.parse(error.message);
    return data.detail || error.message;
  } catch {
    return error.message;
  }
}

function QuestionOption({ question }) {
  return (
    <>
      {question.text}
      <Typography component="span" color="text.secondary" sx={{ ml: 1 }}>
        ({getQuestionTypeLabel(question.qtype)})
      </Typography>
    </>
  );
}

function isRegressionFeatureQuestion(question, targetQuestionId) {
  return (
    isQuestionSupportedForAnalysis(question, "regression", "feature")
    && Number(question.id) !== Number(targetQuestionId)
  );
}

function isLogisticFeatureQuestion(question, targetQuestionId) {
  return (
    isQuestionSupportedForAnalysis(question, "logistic_regression", "feature")
    && Number(question.id) !== Number(targetQuestionId)
  );
}

function SectionFields({ section, questions, updateSection }) {
  if (section.type === "correlation") {
    const availableQuestions = questions.filter((question) => isQuestionSupportedForAnalysis(question, "correlation"));

    return (
      <Stack spacing={2}>
        <FormControl fullWidth>
          <InputLabel>Метод</InputLabel>
          <Select
            label="Метод"
            value={section.method}
            onChange={(event) => updateSection(section.id, { method: event.target.value })}
          >
            <MenuItem value="pearson">Pearson</MenuItem>
            <MenuItem value="spearman">Spearman</MenuItem>
            <MenuItem value="kendall">Kendall</MenuItem>
          </Select>
        </FormControl>

        <FormControl fullWidth>
          <InputLabel>Вопросы</InputLabel>
          <Select
            multiple
            label="Вопросы"
            value={section.questionIds}
            renderValue={(selected) => `${selected.length} выбрано`}
            onChange={(event) => updateSection(section.id, { questionIds: event.target.value })}
          >
            {availableQuestions.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <Checkbox checked={section.questionIds.includes(question.id)} />
                <ListItemText primary={<QuestionOption question={question} />} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>
    );
  }

  if (section.type === "crosstab" || section.type === "chi_square") {
    const availableQuestions = questions.filter((question) => isQuestionSupportedForAnalysis(question, section.type));

    return (
      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        <FormControl fullWidth>
          <InputLabel>Строки</InputLabel>
          <Select
            label="Строки"
            value={section.rowQuestionId}
            onChange={(event) => updateSection(section.id, { rowQuestionId: event.target.value })}
          >
            {availableQuestions.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <QuestionOption question={question} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl fullWidth>
          <InputLabel>Столбцы</InputLabel>
          <Select
            label="Столбцы"
            value={section.columnQuestionId}
            onChange={(event) => updateSection(section.id, { columnQuestionId: event.target.value })}
          >
            {availableQuestions.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <QuestionOption question={question} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>
    );
  }

  if (section.type === "correspondence_analysis") {
    const availableQuestions = questions.filter((question) => isQuestionSupportedForAnalysis(question, "correspondence_analysis"));

    return (
      <Stack spacing={2}>
        <Alert severity="info">
          Анализ соответствий применяется к таблице сопряжённости двух категориальных переменных.
        </Alert>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <FormControl fullWidth>
            <InputLabel>Строки</InputLabel>
            <Select
              label="Строки"
              value={section.rowQuestionId}
              onChange={(event) => updateSection(section.id, { rowQuestionId: event.target.value })}
            >
              {availableQuestions.map((question) => (
                <MenuItem key={question.id} value={question.id}>
                  <QuestionOption question={question} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Столбцы</InputLabel>
            <Select
              label="Столбцы"
              value={section.columnQuestionId}
              onChange={(event) => updateSection(section.id, { columnQuestionId: event.target.value })}
            >
              {availableQuestions.map((question) => (
                <MenuItem key={question.id} value={question.id}>
                  <QuestionOption question={question} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            fullWidth
            type="number"
            label="Количество измерений"
            inputProps={{ min: 1, max: 5 }}
            value={section.n_dimensions}
            onChange={(event) => updateSection(section.id, { n_dimensions: Number(event.target.value) })}
          />
        </Stack>

        <FormControlLabel
          control={
            <Checkbox
              checked={section.post_hoc}
              onChange={(event) => updateSection(section.id, { post_hoc: event.target.checked })}
            />
          }
          label="Выполнить post-hoc сравнения"
        />

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <FormControl fullWidth disabled={!section.post_hoc}>
            <InputLabel>Post-hoc метод</InputLabel>
            <Select
              label="Post-hoc метод"
              value={section.post_hoc_method}
              onChange={(event) => updateSection(section.id, { post_hoc_method: event.target.value })}
            >
              <MenuItem value="auto">Автоматически</MenuItem>
              <MenuItem value="pairwise_t_test">Попарные t-tests</MenuItem>
              <MenuItem value="pairwise_mann_whitney">Попарные Mann-Whitney</MenuItem>
              <MenuItem value="tukey_hsd">Tukey HSD</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth disabled={!section.post_hoc || section.post_hoc_method === "tukey_hsd"}>
            <InputLabel>Поправка p-value</InputLabel>
            <Select
              label="Поправка p-value"
              value={section.p_adjust}
              onChange={(event) => updateSection(section.id, { p_adjust: event.target.value })}
            >
              <MenuItem value="bonferroni">Bonferroni</MenuItem>
              <MenuItem value="holm">Holm</MenuItem>
            </Select>
          </FormControl>
        </Stack>

        {section.post_hoc && (
          <Alert severity="info">
            {section.method === "anova"
              ? "Post-hoc сравнения помогут определить, между какими группами есть различия."
              : section.method === "kruskal_wallis"
                ? "Для Kruskal-Wallis будут использованы попарные Mann-Whitney U с поправкой p-value."
                : "Post-hoc обычно не требуется для двухгрупповых тестов."}
          </Alert>
        )}
      </Stack>
    );
  }

  if (section.type === "logistic_regression") {
    const targets = questions.filter((question) => isQuestionSupportedForAnalysis(question, "logistic_regression", "target"));
    const features = questions.filter((question) => isLogisticFeatureQuestion(question, section.targetQuestionId));

    return (
      <Stack spacing={2}>
        <Alert severity="info">
          Логистическая регрессия анализирует бинарный исход. В MVP целевая переменная должна быть вопросом Да/Нет.
        </Alert>

        <FormControl fullWidth>
          <InputLabel>Целевая переменная</InputLabel>
          <Select
            label="Целевая переменная"
            value={section.targetQuestionId}
            onChange={(event) => updateSection(section.id, {
              targetQuestionId: event.target.value,
              featureQuestionIds: section.featureQuestionIds.filter((id) => Number(id) !== Number(event.target.value)),
            })}
          >
            {targets.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <QuestionOption question={question} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl fullWidth>
          <InputLabel>Факторы</InputLabel>
          <Select
            multiple
            label="Факторы"
            value={section.featureQuestionIds}
            renderValue={(selected) => `${selected.length} выбрано`}
            onChange={(event) => updateSection(section.id, { featureQuestionIds: event.target.value })}
          >
            {features.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <Checkbox checked={section.featureQuestionIds.includes(question.id)} />
                <ListItemText primary={<QuestionOption question={question} />} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControlLabel
          control={
            <Checkbox
              checked={section.include_intercept}
              onChange={(event) => updateSection(section.id, { include_intercept: event.target.checked })}
            />
          }
          label="Включить intercept"
        />

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            fullWidth
            type="number"
            label="threshold"
            inputProps={{ min: 0.01, max: 0.99, step: 0.01 }}
            value={section.threshold}
            onChange={(event) => updateSection(section.id, { threshold: Number(event.target.value) })}
          />

          <FormControl fullWidth>
            <InputLabel>regularization</InputLabel>
            <Select
              label="regularization"
              value={section.regularization}
              onChange={(event) => updateSection(section.id, { regularization: event.target.value })}
            >
              <MenuItem value="l2">l2</MenuItem>
              <MenuItem value="none">none</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            type="number"
            label="lambda"
            inputProps={{ min: 0, max: 10, step: 0.01 }}
            value={section.lambda_}
            onChange={(event) => updateSection(section.id, { lambda_: Number(event.target.value) })}
          />
        </Stack>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            fullWidth
            type="number"
            label="max_iter"
            inputProps={{ min: 50, max: 10000 }}
            value={section.max_iter}
            onChange={(event) => updateSection(section.id, { max_iter: Number(event.target.value) })}
          />

          <TextField
            fullWidth
            type="number"
            label="learning_rate"
            inputProps={{ min: 0.0001, max: 1, step: 0.01 }}
            value={section.learning_rate}
            onChange={(event) => updateSection(section.id, { learning_rate: Number(event.target.value) })}
          />
        </Stack>
      </Stack>
    );
  }

  if (section.type === "factor_analysis") {
    const availableQuestions = questions.filter((question) => isQuestionSupportedForAnalysis(question, "factor_analysis"));
    const maxFactors = Math.max(1, Math.min(5, (section.questionIds?.length || 0) - 1));
    const factorOptions = Array.from({ length: maxFactors }, (_, index) => index + 1);
    const selectedFactors = Math.min(section.n_factors || 2, maxFactors);

    return (
      <Stack spacing={2}>
        {(section.questionIds || []).length < 3 && (
          <Alert severity="info">Для факторного анализа требуется минимум три переменные.</Alert>
        )}

        <FormControl fullWidth>
          <InputLabel>Переменные</InputLabel>
          <Select
            multiple
            label="Переменные"
            value={section.questionIds}
            renderValue={(selected) => `${selected.length} выбрано`}
            onChange={(event) => {
              const questionIds = event.target.value;
              const nextMaxFactors = Math.max(1, Math.min(5, questionIds.length - 1));
              updateSection(section.id, {
                questionIds,
                n_factors: Math.min(section.n_factors || 2, nextMaxFactors),
              });
            }}
          >
            {availableQuestions.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <Checkbox checked={section.questionIds.includes(question.id)} />
                <ListItemText primary={<QuestionOption question={question} />} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <FormControl fullWidth>
            <InputLabel>Количество факторов</InputLabel>
            <Select
              label="Количество факторов"
              value={selectedFactors}
              onChange={(event) => updateSection(section.id, { n_factors: event.target.value })}
            >
              {factorOptions.map((value) => (
                <MenuItem key={value} value={value}>
                  {value}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Rotation</InputLabel>
            <Select
              label="Rotation"
              value={section.rotation}
              onChange={(event) => updateSection(section.id, { rotation: event.target.value })}
            >
              <MenuItem value="varimax">varimax</MenuItem>
              <MenuItem value="none">none</MenuItem>
            </Select>
          </FormControl>
        </Stack>

        <FormControlLabel
          control={
            <Checkbox
              checked={section.standardize}
              onChange={(event) => updateSection(section.id, { standardize: event.target.checked })}
            />
          }
          label="Стандартизировать переменные"
        />
      </Stack>
    );
  }

  if (section.type === "cluster_analysis") {
    const availableQuestions = questions.filter((question) => isQuestionSupportedForAnalysis(question, "cluster_analysis"));
    const profileQuestions = questions.filter((question) => isQuestionSupportedForAnalysis(question, "cluster_analysis", "profile"));

    return (
      <Stack spacing={2}>
        <Alert severity="info">
          Профили кластеров помогают интерпретировать сегменты: система сравнит каждый кластер с общей выборкой и покажет наиболее отличающиеся признаки.
        </Alert>

        {(section.questionIds || []).length < 2 && (
          <Alert severity="info">Для кластерного анализа требуется минимум две переменные.</Alert>
        )}

        <FormControl fullWidth>
          <InputLabel>Переменные для кластеризации</InputLabel>
          <Select
            multiple
            label="Переменные для кластеризации"
            value={section.questionIds}
            renderValue={(selected) => `${selected.length} выбрано`}
            onChange={(event) => updateSection(section.id, { questionIds: event.target.value })}
          >
            {availableQuestions.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <Checkbox checked={section.questionIds.includes(question.id)} />
                <ListItemText primary={<QuestionOption question={question} />} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl fullWidth>
          <InputLabel>Переменные для описания кластеров</InputLabel>
          <Select
            multiple
            label="Переменные для описания кластеров"
            value={section.profileQuestionIds || []}
            renderValue={(selected) => selected.length ? `${selected.length} выбрано` : "Используются переменные кластеризации"}
            onChange={(event) => updateSection(section.id, { profileQuestionIds: event.target.value })}
          >
            {profileQuestions.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <Checkbox checked={(section.profileQuestionIds || []).includes(question.id)} />
                <ListItemText primary={<QuestionOption question={question} />} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {!(section.profileQuestionIds || []).length && (
          <Alert severity="info">
            Если не выбрать переменные профиля, будут использованы переменные кластеризации.
          </Alert>
        )}

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            fullWidth
            type="number"
            label="n_clusters"
            inputProps={{ min: 2, max: 10 }}
            value={section.n_clusters}
            onChange={(event) => updateSection(section.id, { n_clusters: Number(event.target.value) })}
          />
          <TextField
            fullWidth
            type="number"
            label="max_iter"
            inputProps={{ min: 10, max: 1000 }}
            value={section.max_iter}
            onChange={(event) => updateSection(section.id, { max_iter: Number(event.target.value) })}
          />
          <TextField
            fullWidth
            type="number"
            label="Количество ключевых отличий"
            inputProps={{ min: 1, max: 20 }}
            value={section.max_profile_features}
            onChange={(event) => updateSection(section.id, { max_profile_features: Number(event.target.value) })}
          />
        </Stack>

        <FormControlLabel
          control={
            <Checkbox
              checked={section.standardize}
              onChange={(event) => updateSection(section.id, { standardize: event.target.checked })}
            />
          }
          label="Стандартизировать переменные"
        />
      </Stack>
    );
  }

  if (section.type === "group_comparison") {
    const groupQuestions = questions.filter((question) => isQuestionSupportedForAnalysis(question, "group_comparison", "group"));
    const valueQuestions = questions.filter((question) => (
      isQuestionSupportedForAnalysis(question, "group_comparison", "value")
      && Number(question.id) !== Number(section.groupQuestionId)
    ));

    return (
      <Stack spacing={2}>
        <Alert severity="info">
          t-test и Mann-Whitney требуют ровно 2 группы; ANOVA и Kruskal-Wallis подходят для 2+ групп.
        </Alert>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <FormControl fullWidth>
            <InputLabel>Группирующая переменная</InputLabel>
            <Select
              label="Группирующая переменная"
              value={section.groupQuestionId}
              onChange={(event) => updateSection(section.id, {
                groupQuestionId: event.target.value,
                valueQuestionId: Number(event.target.value) === Number(section.valueQuestionId) ? "" : section.valueQuestionId,
              })}
            >
              {groupQuestions.map((question) => (
                <MenuItem key={question.id} value={question.id}>
                  <QuestionOption question={question} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Показатель</InputLabel>
            <Select
              label="Показатель"
              value={section.valueQuestionId}
              onChange={(event) => updateSection(section.id, { valueQuestionId: event.target.value })}
            >
              {valueQuestions.map((question) => (
                <MenuItem key={question.id} value={question.id}>
                  <QuestionOption question={question} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <FormControl fullWidth>
            <InputLabel>Метод</InputLabel>
            <Select
              label="Метод"
              value={section.method}
              onChange={(event) => updateSection(section.id, { method: event.target.value })}
            >
              <MenuItem value="t_test">Welch t-test</MenuItem>
              <MenuItem value="anova">ANOVA</MenuItem>
              <MenuItem value="mann_whitney">Mann-Whitney U</MenuItem>
              <MenuItem value="kruskal_wallis">Kruskal-Wallis</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            type="number"
            label="alpha"
            inputProps={{ min: 0.001, max: 0.2, step: 0.001 }}
            value={section.alpha}
            onChange={(event) => updateSection(section.id, { alpha: Number(event.target.value) })}
          />
        </Stack>
      </Stack>
    );
  }

  if (section.type === "reliability_analysis") {
    const availableQuestions = questions.filter((question) => isQuestionSupportedForAnalysis(question, "reliability_analysis"));

    return (
      <Stack spacing={2}>
        <Alert severity="info">
          Cronbach’s alpha используется для оценки внутренней согласованности набора вопросов, измеряющих одну шкалу. Выберите минимум два вопроса.
        </Alert>

        <FormControl fullWidth>
          <InputLabel>Переменные шкалы</InputLabel>
          <Select
            multiple
            label="Переменные шкалы"
            value={section.questionIds}
            renderValue={(selected) => `${selected.length} выбрано`}
            onChange={(event) => updateSection(section.id, { questionIds: event.target.value })}
          >
            {availableQuestions.map((question) => (
              <MenuItem key={question.id} value={question.id}>
                <Checkbox checked={section.questionIds.includes(question.id)} />
                <ListItemText primary={<QuestionOption question={question} />} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControlLabel
          control={
            <Checkbox
              checked={section.standardize}
              onChange={(event) => updateSection(section.id, { standardize: event.target.checked })}
            />
          }
          label="Использовать стандартизированную alpha"
        />
      </Stack>
    );
  }

  const targets = questions.filter((question) => isQuestionSupportedForAnalysis(question, "regression", "target"));
  const features = questions.filter((question) => isRegressionFeatureQuestion(question, section.targetQuestionId));

  return (
    <Stack spacing={2}>
      <FormControl fullWidth>
        <InputLabel>Целевая переменная</InputLabel>
        <Select
          label="Целевая переменная"
          value={section.targetQuestionId}
          onChange={(event) => updateSection(section.id, {
            targetQuestionId: event.target.value,
            featureQuestionIds: section.featureQuestionIds.filter((id) => Number(id) !== Number(event.target.value)),
          })}
        >
          {targets.map((question) => (
            <MenuItem key={question.id} value={question.id}>
              <QuestionOption question={question} />
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <FormControl fullWidth>
        <InputLabel>Факторы</InputLabel>
        <Select
          multiple
          label="Факторы"
          value={section.featureQuestionIds}
          renderValue={(selected) => `${selected.length} выбрано`}
          onChange={(event) => updateSection(section.id, { featureQuestionIds: event.target.value })}
        >
          {features.map((question) => (
            <MenuItem key={question.id} value={question.id}>
              <Checkbox checked={section.featureQuestionIds.includes(question.id)} />
              <ListItemText primary={<QuestionOption question={question} />} />
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <FormControlLabel
        control={
          <Checkbox
            checked={section.include_intercept}
            onChange={(event) => updateSection(section.id, { include_intercept: event.target.checked })}
          />
        }
        label="Включить intercept"
      />
    </Stack>
  );
}

export default function ReportBuilderPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [reportTitle, setReportTitle] = useState("Аналитический отчёт");
  const [sections, setSections] = useState([]);
  const [newSectionType, setNewSectionType] = useState("correlation");
  const [isRunning, setIsRunning] = useState(false);
  const [pageError, setPageError] = useState("");

  const { data: survey, isLoading } = useQuery({
    queryKey: ["admin-survey", id],
    enabled: !!id,
    queryFn: () => fetchAdminSurveyById(id),
  });

  const questions = useMemo(() => getAllSurveyQuestions(survey), [survey]);
  const questionsById = useMemo(() => new Map(questions.map((question) => [Number(question.id), question])), [questions]);

  const addSection = () => {
    setSections((current) => [...current, createSection(newSectionType)]);
  };

  const updateSection = (sectionId, patch) => {
    setSections((current) => current.map((section) => (
      section.id === sectionId ? { ...section, ...patch } : section
    )));
  };

  const removeSection = (sectionId) => {
    setSections((current) => current.filter((section) => section.id !== sectionId));
  };

  const buildReport = async () => {
    setPageError("");
    if (!sections.length) {
      setPageError("Добавьте хотя бы один аналитический блок.");
      return;
    }

    setIsRunning(true);
    const resultSections = [];

    for (const section of sections) {
      try {
        const payload = buildSectionPayload(id, section, questionsById);
        const data = await API_BY_TYPE[section.type](payload);
        resultSections.push({
          id: section.id,
          type: section.type,
          title: section.title,
          config: section,
          result: data,
          error: null,
        });
      } catch (error) {
        resultSections.push({
          id: section.id,
          type: section.type,
          title: section.title,
          config: section,
          result: null,
          error: getErrorMessage(error),
        });
      }
    }

    const reportResult = {
      title: reportTitle,
      survey: {
        id: survey.id,
        title: survey.title,
      },
      generatedAt: new Date().toISOString(),
      sections: resultSections,
    };

    // sessionStorage.setItem("advancedReportResult", JSON.stringify(reportResult));
    
    try {
      const savedReport = await createAnalysisReport({
        survey: Number(id),
        title: reportTitle,
        config: {
          title: reportTitle,
          sections,
        },
        result: reportResult,
      });

      if (!savedReport?.id) {
        throw new Error("Backend did not return saved report id.");
      }

      navigate(`/analytics/surveys/${id}/report-result/${savedReport.id}`);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsRunning(false);
    }
  };

  if (isLoading || !survey) return null;

  return (
    <Container maxWidth={false} sx={{ mt: 4, width: "100%" }}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 1 }}>
            Конструктор аналитического отчёта
          </Typography>
          <Typography color="text.secondary">
            {survey.title}
          </Typography>
        </Box>
        <Button variant="outlined" onClick={() => navigate(`/analytics/surveys/${id}`)}>
          Назад к аналитике
        </Button>
      </Stack>

      {pageError && <Alert severity="warning" sx={{ mb: 2 }}>{pageError}</Alert>}

      <TextField
        fullWidth
        label="Название отчёта"
        value={reportTitle}
        onChange={(event) => setReportTitle(event.target.value)}
        sx={{ mb: 3 }}
      />

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 3 }}>
        <FormControl sx={{ minWidth: 260 }}>
          <InputLabel>Тип анализа</InputLabel>
          <Select
            label="Тип анализа"
            value={newSectionType}
            onChange={(event) => setNewSectionType(event.target.value)}
          >
            {ANALYSIS_TYPES.map((type) => (
              <MenuItem key={type.value} value={type.value}>
                {type.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button variant="contained" startIcon={<AddIcon />} onClick={addSection}>
          Добавить блок
        </Button>
      </Stack>

      <Stack spacing={2} sx={{ mb: 3 }}>
        {sections.map((section, index) => (
          <Card key={section.id}>
            <CardContent>
              <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
                <TextField
                  fullWidth
                  label={`Блок ${index + 1}`}
                  value={section.title}
                  onChange={(event) => updateSection(section.id, { title: event.target.value })}
                />
                <Button
                  color="error"
                  variant="outlined"
                  startIcon={<DeleteIcon />}
                  onClick={() => removeSection(section.id)}
                  sx={{ minWidth: 130 }}
                >
                  Удалить
                </Button>
              </Stack>

              <SectionFields section={section} questions={questions} updateSection={updateSection} />
            </CardContent>
          </Card>
        ))}
      </Stack>

      {!sections.length && (
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Добавьте первый блок анализа, чтобы собрать отчёт.
        </Typography>
      )}

      <Button
        variant="contained"
        size="large"
        startIcon={<PlayArrowIcon />}
        disabled={isRunning}
        onClick={buildReport}
      >
        {isRunning ? "Формирование..." : "Сформировать отчёт"}
      </Button>
    </Container>
  );
}
