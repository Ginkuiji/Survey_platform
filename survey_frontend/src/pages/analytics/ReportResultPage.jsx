import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useQuery } from "@tanstack/react-query";
import {
  fetchAnalysisReportById,
  fetchReportMatplotlibChart,
} from "../../api/analytics";
import {
  ClusterSizeChart,
  ClusterTopFeaturesChart,
  CorrespondenceInertiaChart,
  CorrelationHeatmap,
  CrosstabStackedBar,
  FactorLoadingsHeatmap,
  FactorScreeChart,
  GroupComparisonMeanChart,
  LogisticOddsRatioChart,
  LogisticProbabilityHistogram,
  MissingAnalysisChart,
  RegressionCoefficientChart,
  ReliabilityItemChart,
  ScaleIndexDistributionChart,
  TimeDistributionChart,
  TimeScreenoutReasonsChart,
} from "./reportCharts";

const SECTION_LABELS = {
  correlation: "Корреляционный анализ",
  crosstab: "Таблица сопряжённости",
  chi_square: "χ²-критерий",
  correspondence_analysis: "Анализ соответствий",
  regression: "Линейная регрессия",
  logistic_regression: "Логистическая регрессия",
  factor_analysis: "Факторный анализ",
  cluster_analysis: "Кластерный анализ",
  group_comparison: "Сравнение групп",
  time_analysis: "Анализ времени прохождения и отсева",
  reliability_analysis: "Надёжность шкалы",
  scale_index: "Индекс шкалы",
  missing_analysis: "Анализ пропусков",
};

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (typeof value !== "number") return String(value);
  return Number.isInteger(value) ? String(value) : value.toFixed(4);
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function formatDurationSeconds(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const seconds = Math.round(Number(value));
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (minutes <= 0) return `${rest} сек.`;
  return `${minutes} мин. ${rest} сек.`;
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function useStoredReport(reportId) {
  const { data: report, isLoading, error } = useQuery({
    queryKey: ["analysis-report", reportId],
    enabled: !!reportId,
    queryFn: () => fetchAnalysisReportById(reportId),
  });

  let parsedReport = null;

  if (report?.result) {
    try {
      parsedReport =
        typeof report.result === "string"
          ? JSON.parse(report.result)
          : report.result;
    } catch {
      parsedReport = null;
    }
  }

  return {
    report,
    storedReport: parsedReport,
    isLoading,
    error,
  };
}

function getVariableLabel(result, code) {
  if (!code) return "-";
  if (code === "intercept") return "Свободный член";
  return result?.variables_by_code?.[code]?.label || code;
}

const TIME_SUMMARY_LABELS = {
  total_started: "Начали прохождение",
  total_finished: "Завершили прохождение",
  total_completed: "Полностью завершили",
  total_screened_out: "Отсеяны",
  total_active_unfinished: "Активные незавершенные",
  completion_rate: "Доля полных завершений",
  screenout_rate: "Доля отсева",
  finish_rate: "Доля завершивших",
  average_completion_time_seconds: "Среднее время полного прохождения",
  median_completion_time_seconds: "Медианное время полного прохождения",
  min_completion_time_seconds: "Минимальное время полного прохождения",
  max_completion_time_seconds: "Максимальное время полного прохождения",
  average_screenout_time_seconds: "Среднее время до отсева",
  median_screenout_time_seconds: "Медианное время до отсева",
  min_screenout_time_seconds: "Минимальное время до отсева",
  max_screenout_time_seconds: "Максимальное время до отсева",
};

const SCALE_SUMMARY_LABELS = {
  n: "Число наблюдений",
  mean: "Среднее",
  median: "Медиана",
  std: "Стандартное отклонение",
  variance: "Дисперсия",
  min: "Мини",
  max: "Макс",
  p25: "25-й процентиль",
  p75: "75-й процентиль",
  iqr: "Межквартильный размах",
};

const MISSING_SUMMARY_LABELS = {
  total_shown_slots: "Всего показанных вопросов",
  total_answered_slots: "Всего полученных ответов",
  total_skipped_slots: "Всего пропущенных показанных вопросов",
  total_not_shown_slots: "Всего непоказанных вопросов из-за ветвления",
  overall_skip_rate_shown: "Общая доля пропусков среди показанных",
  overall_visibility_rate: "Общая доля видимости вопросов",
};

function ReportSectionCard({ section, children, onRequestChart, serverChart }) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          alignItems={{ xs: "flex-start", sm: "center" }}
          justifyContent="space-between"
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h6">
              {section.title || SECTION_LABELS[section.type] || section.type}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              {SECTION_LABELS[section.type] || section.type}
            </Typography>
          </Box>

          <Stack direction="row" spacing={1} alignItems="center">
            {section.result?.analysis_type && (
              <Chip label={section.result.analysis_type} />
            )}
            <Button
              size="small"
              variant="outlined"
              disabled={serverChart?.loading}
              onClick={() => onRequestChart?.(section)}
            >
              {serverChart?.loading ? "Построение..." : "Получить график"}
            </Button>
          </Stack>
        </Stack>

        {serverChart?.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {serverChart.error}
          </Alert>
        )}

        {serverChart?.url && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Статистический график Matplotlib
            </Typography>
            <Box
              component="img"
              src={serverChart.url}
              alt="Статистический график"
              sx={{
                width: "100%",
                maxWidth: "100%",
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 1,
                bgcolor: "background.paper",
              }}
            />
          </Box>
        )}

        {children}
      </CardContent>
    </Card>
  );
}

function renderCorrelationSection(section) {
  const result = section.result;
  const variables = result?.variables || [];
  const matrix = result?.matrix || [];
  const pValues = result?.p_values || [];
  const nMatrix = result?.n_matrix || [];

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Метод: ${result?.method || section.config?.method || "—"}`} />
        <Chip label={`Датасет: ${result?.dataset_size ?? "—"}`} />
      </Stack>

      <CorrelationHeatmap result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Переменная</TableCell>
              {variables.map((variable) => (
                <TableCell key={variable.code} align="center">
                  {variable.label || variable.code}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {variables.map((variable, rowIndex) => (
              <TableRow key={variable.code}>
                <TableCell component="th" scope="row">
                  {variable.label || variable.code}
                </TableCell>
                {variables.map((columnVariable, columnIndex) => (
                  <TableCell key={columnVariable.code} align="center">
                    <Typography>{formatNumber(matrix[rowIndex]?.[columnIndex])}</Typography>
                    <Typography color="text.secondary" variant="caption">
                      p={formatNumber(pValues[rowIndex]?.[columnIndex])}; n={formatNumber(nMatrix[rowIndex]?.[columnIndex])}
                    </Typography>
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Stack>
  );
}

function renderCrosstabTable(crosstab) {
  const rows = crosstab?.rows || [];
  const columnValues = rows[0]?.columns?.map((column) => column.value) || [];

  if (!rows.length) {
    return <Typography color="text.secondary">Нет данных для таблицы сопряжённости.</Typography>;
  }

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>{crosstab.row_variable}</TableCell>
            {columnValues.map((value) => (
              <TableCell key={value} align="center">
                {value}
              </TableCell>
            ))}
            <TableCell align="center">Итого</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.value}>
              <TableCell component="th" scope="row">
                {row.value}
              </TableCell>
              {row.columns.map((column) => (
                <TableCell key={column.value} align="center">
                  <Typography>{column.count}</Typography>
                  <Typography color="text.secondary" variant="caption">
                    по строке {formatNumber(column.percent_row)}% · от общего числа {formatNumber(column.percent_total)}%
                  </Typography>
                </TableCell>
              ))}
              <TableCell align="center">{row.total}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Typography color="text.secondary" variant="body2" sx={{ mt: 1 }}>
        Всего: {crosstab.total}
      </Typography>
    </Box>
  );
}

function renderCrosstabSection(section) {
  return (
    <Stack spacing={3}>
      <CrosstabStackedBar crosstab={section.result?.crosstab} />
      {renderCrosstabTable(section.result?.crosstab)}
    </Stack>
  );
}

function renderExpectedTable(expected) {
  if (!expected?.length) {
    return <Typography color="text.secondary">Ожидаемые величины недоступны.</Typography>;
  }

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Строка</TableCell>
            {expected[0].map((_, index) => (
              <TableCell key={index} align="center">
                C{index + 1}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {expected.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              <TableCell>R{rowIndex + 1}</TableCell>
              {row.map((value, columnIndex) => (
                <TableCell key={columnIndex} align="center">
                  {formatNumber(value)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

function renderChiSquareSection(section) {
  const chiSquare = section.result?.chi_square;
  const cramersV = section.result?.cramers_v;

  return (
    <Stack spacing={3}>
      <CrosstabStackedBar crosstab={section.result?.crosstab} />

      {renderCrosstabTable(section.result?.crosstab)}

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`χ²: ${formatNumber(chiSquare?.chi2)}`} />
        <Chip label={`p-value: ${formatNumber(chiSquare?.p_value)}`} />
        <Chip label={`Степени свободы: ${formatNumber(chiSquare?.dof)}`} />
        <Chip label={`V Крамера: ${formatNumber(cramersV?.cramers_v)}`} />
        <Chip label={`Сила связи: ${cramersV?.interpretation || "—"}`} />
        <Chip label={`n: ${formatNumber(cramersV?.n)}`} />
        <Chip label={`${formatNumber(cramersV?.rows)}×${formatNumber(cramersV?.columns)}`} />
      </Stack>

      <Typography color="text.secondary" variant="body2">
        V Крамера показывает силу связи между категориальными переменными от 0 до 1.
      </Typography>

      <Box>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Ожидаемые величины
        </Typography>
        {renderExpectedTable(chiSquare?.expected)}
      </Box>
    </Stack>
  );
}

function valuesByDimension(items = []) {
  return new Map(items.map((item) => [item.dimension, item.value]));
}

function renderCorrespondenceCoordinatesTable(title, dimensions, points) {
  const dimensionNames = dimensions.map((dimension) => dimension.dimension);

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        {title}
      </Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Категория</TableCell>
            <TableCell align="right">Масса</TableCell>
            {dimensionNames.map((dimension) => (
              <TableCell key={dimension} align="right">{dimension}</TableCell>
            ))}
            {dimensionNames.map((dimension) => (
              <TableCell key={`${dimension}-contribution`} align="right">Вклад {dimension}</TableCell>
            ))}
            <TableCell align="right">Cos²</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {points.map((point) => {
            const coordinates = valuesByDimension(point.coordinates);
            const contributions = valuesByDimension(point.contributions);
            return (
              <TableRow key={`${title}-${point.value}`}>
                <TableCell>{point.label || point.value}</TableCell>
                <TableCell align="right">{formatNumber(point.mass)}</TableCell>
                {dimensionNames.map((dimension) => (
                  <TableCell key={dimension} align="right">{formatNumber(coordinates.get(dimension))}</TableCell>
                ))}
                {dimensionNames.map((dimension) => (
                  <TableCell key={`${dimension}-contribution`} align="right">{formatNumber(contributions.get(dimension))}</TableCell>
                ))}
                <TableCell align="right">{formatNumber(point.cos2)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Box>
  );
}

function renderCorrespondenceAnalysisSection(section) {
  const result = section.result || {};
  const dimensions = result.dimensions || [];

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label="Метод: анализ соответствий" />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Строк: ${formatNumber(result.n_rows)}`} />
        <Chip label={`Столбцов: ${formatNumber(result.n_columns)}`} />
        <Chip label={`Измерений: ${formatNumber(result.n_dimensions)}`} />
        <Chip label={`Общая инерция: ${formatNumber(result.total_inertia)}`} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <CorrespondenceInertiaChart result={result} />

      <Box>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Таблица сопряжённости
        </Typography>
        <CrosstabStackedBar crosstab={result.crosstab} />
        {renderCrosstabTable(result.crosstab)}
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Инерция по измерениям
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Измерение</TableCell>
              <TableCell align="right">Собственное значение</TableCell>
              <TableCell align="right">Объясненная инерция</TableCell>
              <TableCell align="right">%</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {dimensions.map((dimension) => (
              <TableRow key={dimension.dimension}>
                <TableCell>{dimension.dimension}</TableCell>
                <TableCell align="right">{formatNumber(dimension.eigenvalue)}</TableCell>
                <TableCell align="right">{formatNumber(dimension.explained_inertia)}</TableCell>
                <TableCell align="right">{formatPercent(dimension.explained_inertia)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      {renderCorrespondenceCoordinatesTable("Координаты строк", dimensions, result.row_coordinates || [])}
      {renderCorrespondenceCoordinatesTable("Координаты столбцов", dimensions, result.column_coordinates || [])}
    </Stack>
  );
}

function renderRegressionSection(section) {
  const result = section.result;
  const featureLabels = (result?.features || []).map(code => getVariableLabel(result, code));

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Зависимая переменная: ${getVariableLabel(result, result?.target)}`} />
        <Chip label={`n: ${formatNumber(result?.n)}`} />
        <Chip label={`Предикторов: ${featureLabels.length}`} />
        <Chip label={`R²: ${formatNumber(result?.r2)}`} />
        <Chip label={`Скорректированный R²: ${formatNumber(result?.adjusted_r2)}`} />
      </Stack>

      <Typography color="text.secondary" variant="body2">
        Предикторы: {(result?.features || []).map(code => getVariableLabel(result, code)).join(", ") || "—"}
      </Typography>

      <RegressionCoefficientChart result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Коэффициент</TableCell>
              <TableCell align="right">Значение</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(result?.coefficients || []).map((coefficient) => (
              <TableRow key={coefficient.name}>
                <TableCell>{getVariableLabel(result, coefficient.name)}</TableCell>
                <TableCell align="right">{formatNumber(coefficient.value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Stack>
  );
}

function renderLogisticRegressionSection(section) {
  const result = section.result || {};
  const metrics = result.metrics || {};
  const confusionMatrix = result.confusion_matrix || {};
  const featureLabels = (result.features || []).map(code => getVariableLabel(result, code));

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Метод: ${result.method || "—"}`} />
        <Chip label={`Зависимая переменная: ${getVariableLabel(result, result.target)}`} />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Положительный класс: ${formatNumber(result.positive_class_count)}`} />
        <Chip label={`Отрицательный класс: ${formatNumber(result.negative_class_count)}`} />
        <Chip label={`Порог классификации: ${formatNumber(result.threshold)}`} />
        <Chip label={`Доля верных классификаций: ${formatNumber(metrics.accuracy)}`} />
        <Chip label={`Точность: ${formatNumber(metrics.precision)}`} />
        <Chip label={`Полнота: ${formatNumber(metrics.recall)}`} />
        <Chip label={`F1: ${formatNumber(metrics.f1)}`} />
        <Chip label={`McFadden R²: ${formatNumber(metrics.mcfadden_r2)}`} />
      </Stack>

      <Typography color="text.secondary" variant="body2">
        Предикторы: {featureLabels.join(", ") || "—"}
      </Typography>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <LogisticOddsRatioChart result={result} />
      <LogisticProbabilityHistogram result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Матрица ошибок
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell />
              <TableCell align="right">Прогноз: 0</TableCell>
              <TableCell align="right">Прогноз: 1</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell>Факт: 0</TableCell>
              <TableCell align="right">{formatNumber(confusionMatrix.tn)}</TableCell>
              <TableCell align="right">{formatNumber(confusionMatrix.fp)}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Факт: 1</TableCell>
              <TableCell align="right">{formatNumber(confusionMatrix.fn)}</TableCell>
              <TableCell align="right">{formatNumber(confusionMatrix.tp)}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Коэффициенты
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Переменная</TableCell>
              <TableCell align="right">Коэффициент</TableCell>
              <TableCell align="right">Отношение шансов</TableCell>
              <TableCell>Интерпретация</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(result.coefficients || []).map((coefficient) => (
              <TableRow key={coefficient.name}>
                <TableCell>{getVariableLabel(result, coefficient.name)}</TableCell>
                <TableCell align="right">{formatNumber(coefficient.coefficient)}</TableCell>
                <TableCell align="right">{formatNumber(coefficient.odds_ratio)}</TableCell>
                <TableCell>{coefficient.interpretation || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Typography color="text.secondary" variant="body2">
        Прогнозы сохранены в результате API; в этом представлении показана только сводка модели.
      </Typography>
    </Stack>
  );
}

function renderFactorAnalysisSection(section) {
  const result = section.result || {};
  const explainedVariance = result.explained_variance || [];
  const loadings = result.loadings || [];
  const eigenvalues = result.eigenvalues || [];
  const factorNames = explainedVariance.map(item => item.factor);
  const kmo = result.kmo || {};
  const bartlett = result.bartlett || {};
  const recommendations = result.factor_recommendations || {};
  const scree = result.scree || [];
  const factorScores = result.factor_scores || [];

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Метод: ${result.method || "вЂ”"}`} />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Переменных: ${formatNumber(result.n_variables)}`} />
        <Chip label={`Факторов: ${formatNumber(result.n_factors)}`} />
        <Chip label={`Вращение: ${result.rotation || "вЂ”"}`} />
        <Chip label={`Накопленная объясненная дисперсия: ${formatPercent(result.cumulative_explained_variance)}`} />
        <Chip label={`KMO: ${formatNumber(kmo.overall)}`} />
        <Chip label={`p-value Бартлетта: ${formatNumber(bartlett.p_value)}`} />
        <Chip label={`Kaiser: ${formatNumber(recommendations.kaiser_n_factors)}`} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}
      {(kmo.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}
      {(bartlett.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <FactorScreeChart result={result} />
      <FactorLoadingsHeatmap result={result} />

      <Box>
        <Typography variant="subtitle1">Рекомендация числа факторов</Typography>
        <Typography color="text.secondary" variant="body2">
          {recommendations.message || "—"}
        </Typography>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>KMO</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
          <Chip label={`Общий KMO: ${formatNumber(kmo.overall)}`} />
          <Chip label={kmo.interpretation || "—"} />
        </Stack>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Переменная</TableCell>
              <TableCell align="right">KMO</TableCell>
              <TableCell>Интерпретация</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(kmo.variables || []).map((item) => (
              <TableRow key={item.code}>
                <TableCell>{item.label || item.code}</TableCell>
                <TableCell align="right">{formatNumber(item.kmo)}</TableCell>
                <TableCell>{item.interpretation || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box>
        <Typography variant="subtitle1">Критерий сферичности Бартлетта</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ my: 1 }}>
          <Chip label={`χ²: ${formatNumber(bartlett.chi_square)}`} />
          <Chip label={`Степени свободы: ${formatNumber(bartlett.dof)}`} />
          <Chip label={`p-value: ${formatNumber(bartlett.p_value)}`} />
          <Chip label={`Статистически значимо: ${bartlett.significant === null || bartlett.significant === undefined ? "—" : (bartlett.significant ? "да" : "нет")}`} />
        </Stack>
        <Typography color="text.secondary" variant="body2">
          {bartlett.interpretation || "—"}
        </Typography>
      </Box>

      {scree.length > 0 && (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>Данные графика каменистой осыпи</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Компонента</TableCell>
                <TableCell align="right">Собственное значение</TableCell>
                <TableCell align="right">Объясненная дисперсия</TableCell>
                <TableCell align="right">Накопленная доля</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {scree.map((item) => (
                <TableRow key={item.component}>
                  <TableCell>{item.component}</TableCell>
                  <TableCell align="right">{formatNumber(item.eigenvalue)}</TableCell>
                  <TableCell align="right">{formatPercent(item.explained_variance)}</TableCell>
                  <TableCell align="right">{formatPercent(item.cumulative_explained_variance)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Объясненная дисперсия
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Фактор</TableCell>
              <TableCell align="right">Значение</TableCell>
              <TableCell align="right">Доля</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {explainedVariance.map((item) => (
              <TableRow key={item.factor}>
                <TableCell>{item.factor}</TableCell>
                <TableCell align="right">{formatNumber(item.value)}</TableCell>
                <TableCell align="right">{formatPercent(item.value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Факторные нагрузки
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Переменная</TableCell>
              <TableCell align="right">Общность</TableCell>
              {factorNames.map((factor) => (
                <TableCell key={factor} align="right">{factor}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loadings.map((item) => {
              const factorsByName = new Map((item.factors || []).map(factor => [factor.factor, factor.loading]));
              return (
                <TableRow key={item.variable}>
                  <TableCell>{item.label || item.variable}</TableCell>
                  <TableCell align="right">{formatNumber(item.communality)}</TableCell>
                  {factorNames.map((factor) => (
                    <TableCell key={factor} align="right">{formatNumber(factorsByName.get(factor))}</TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Собственные значения
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Компонента</TableCell>
              <TableCell align="right">Собственное значение</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {eigenvalues.map((value, index) => (
              <TableRow key={index}>
                <TableCell>Компонента {index + 1}</TableCell>
                <TableCell align="right">{formatNumber(value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      {factorScores.length > 0 && (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <Alert severity="info" sx={{ mb: 1 }}>
            Факторные значения рассчитаны; в интерфейсе показаны первые 20.
          </Alert>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID ответа</TableCell>
                {factorScores[0]?.scores?.map((score) => (
                  <TableCell key={score.factor} align="right">{score.factor}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {factorScores.slice(0, 20).map((item, index) => (
                <TableRow key={item.response_id || index}>
                  <TableCell>{item.response_id || "—"}</TableCell>
                  {(item.scores || []).map((score) => (
                    <TableCell key={score.factor} align="right">{formatNumber(score.value)}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}
    </Stack>
  );
}

function renderClusterProfileTable(title, headers, rows) {
  if (!rows.length) return null;
  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        {title}
      </Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            {headers.map((header) => (
              <TableCell key={header.key} align={header.align || "left"}>{header.label}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow key={row.key || index}>
              {headers.map((header) => (
                <TableCell key={header.key} align={header.align || "left"}>
                  {header.render ? header.render(row) : row[header.key]}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

function renderClusterProfiles(profiles) {
  if (!profiles.length) return null;

  const topHeaders = [
    { key: "label", label: "Признак" },
    { key: "type", label: "Тип" },
    { key: "cluster_value", label: "В кластере", align: "right", render: (row) => formatNumber(row.cluster_value) },
    { key: "overall_value", label: "В выборке", align: "right", render: (row) => formatNumber(row.overall_value) },
    { key: "difference", label: "Отличие", align: "right", render: (row) => formatNumber(row.difference) },
    { key: "interpretation", label: "Интерпретация" },
  ];
  const numericHeaders = [
    { key: "label", label: "Переменная" },
    { key: "cluster_mean", label: "Среднее в кластере", align: "right", render: (row) => formatNumber(row.cluster_mean) },
    { key: "overall_mean", label: "Среднее по выборке", align: "right", render: (row) => formatNumber(row.overall_mean) },
    { key: "difference", label: "Разница", align: "right", render: (row) => formatNumber(row.difference) },
    { key: "z_difference", label: "z-разница", align: "right", render: (row) => formatNumber(row.z_difference) },
    { key: "interpretation", label: "Интерпретация" },
  ];
  const binaryHeaders = [
    { key: "label", label: "Признак" },
    { key: "cluster_percent_selected", label: "% в кластере", align: "right", render: (row) => `${formatNumber(row.cluster_percent_selected)}%` },
    { key: "overall_percent_selected", label: "% в выборке", align: "right", render: (row) => `${formatNumber(row.overall_percent_selected)}%` },
    { key: "difference_pp", label: "Разница, п.п.", align: "right", render: (row) => formatNumber(row.difference_pp) },
    { key: "interpretation", label: "Интерпретация" },
  ];
  const categoryHeaders = [
    { key: "variable_label", label: "Переменная" },
    { key: "label", label: "Категория" },
    { key: "cluster_percent", label: "% в кластере", align: "right", render: (row) => `${formatNumber(row.cluster_percent)}%` },
    { key: "overall_percent", label: "% в выборке", align: "right", render: (row) => `${formatNumber(row.overall_percent)}%` },
    { key: "difference_pp", label: "Разница, п.п.", align: "right", render: (row) => formatNumber(row.difference_pp) },
  ];

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1">Профили кластеров</Typography>
      {profiles.map((profile) => {
        const categoryRows = (profile.categorical_summary || []).flatMap((summary) => (
          (summary.categories || []).map((category) => ({
            ...category,
            variable_label: summary.label || summary.variable,
          }))
        ));

        return (
          <Box
            key={profile.cluster}
            sx={{
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              p: 2,
            }}
          >
            <Stack spacing={2}>
              <Box>
                <Typography variant="subtitle1">
                  Кластер {profile.cluster}: {formatNumber(profile.size)} респондентов ({formatNumber(profile.percent)}%)
                </Typography>
                <Typography color="text.secondary" variant="body2">
                  {profile.interpretation || "—"}
                </Typography>
              </Box>

              {renderClusterProfileTable("Ключевые отличия", topHeaders, profile.top_distinguishing_features || [])}
              {renderClusterProfileTable("Числовой профиль", numericHeaders, profile.numeric_summary || [])}
              {renderClusterProfileTable("Бинарный профиль", binaryHeaders, profile.binary_summary || [])}
              {renderClusterProfileTable("Категориальный профиль", categoryHeaders, categoryRows)}
            </Stack>
          </Box>
        );
      })}
    </Stack>
  );
}

function renderClusterAnalysisSection(section) {
  const result = section.result || {};
  const variables = result.variables || [];
  const clusters = result.clusters || [];
  const profiles = result.cluster_profiles || [];

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Метод: ${result.method || "—"}`} />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Переменных: ${formatNumber(result.n_variables)}`} />
        <Chip label={`Кластеров: ${formatNumber(result.n_clusters)}`} />
        <Chip label={`Стандартизация: ${result.standardize ? "да" : "нет"}`} />
        <Chip label={`Инерция: ${formatNumber(result.inertia)}`} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <ClusterSizeChart result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Кластер</TableCell>
              <TableCell align="right">Размер</TableCell>
              <TableCell align="right">Доля</TableCell>
              {variables.map((variable) => (
                <TableCell key={variable.code} align="right">
                  {variable.label || variable.code}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {clusters.map((cluster) => (
              <TableRow key={cluster.cluster}>
                <TableCell>{cluster.cluster}</TableCell>
                <TableCell align="right">{formatNumber(cluster.size)}</TableCell>
                <TableCell align="right">{formatNumber(cluster.percent)}%</TableCell>
                {variables.map((variable) => (
                  <TableCell key={variable.code} align="right">
                    {formatNumber(cluster.centroid?.[variable.code])}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Typography color="text.secondary" variant="body2">
        Принадлежность респондентов к кластерам сохранена в результате для экспорта и API; в этом представлении показана только сводка по кластерам.
      </Typography>

      <ClusterTopFeaturesChart result={result} />

      {renderClusterProfiles(profiles)}
    </Stack>
  );
}

function renderPostHocComparisons(postHoc) {
  if (!postHoc || !postHoc.enabled) return null;
  const comparisons = postHoc.comparisons || [];

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Апостериорные сравнения
      </Typography>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
        <Chip label={`Метод: ${postHoc.method || "—"}`} />
        <Chip label={`Поправка: ${postHoc.p_adjust || "—"}`} />
        <Chip label={`Сравнений: ${postHoc.comparisons_count ?? comparisons.length}`} />
      </Stack>

      {(postHoc.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning" sx={{ mb: 1 }}>{warning}</Alert>
      ))}

      {comparisons.length > 0 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Группа A</TableCell>
              <TableCell>Группа B</TableCell>
              <TableCell>Тест</TableCell>
              <TableCell align="right">Статистика критерия</TableCell>
              <TableCell align="right">p-value</TableCell>
              <TableCell align="right">Скорректированное p</TableCell>
              <TableCell>Статистически значимо</TableCell>
              <TableCell align="right">Разность</TableCell>
              <TableCell align="right">Размер эффекта</TableCell>
              <TableCell>Интерпретация</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {comparisons.map((comparison, index) => {
              const effectSize = comparison.effect_size || {};
              return (
                <TableRow key={`${comparison.group_a}-${comparison.group_b}-${index}`}>
                  <TableCell>{comparison.group_a_label || comparison.group_a}</TableCell>
                  <TableCell>{comparison.group_b_label || comparison.group_b}</TableCell>
                  <TableCell>{comparison.test}</TableCell>
                  <TableCell align="right">{formatNumber(comparison.statistic)}</TableCell>
                  <TableCell align="right">{formatNumber(comparison.p_value)}</TableCell>
                  <TableCell align="right">{formatNumber(comparison.p_adjusted)}</TableCell>
                  <TableCell>{comparison.significant ? "да" : "нет"}</TableCell>
                  <TableCell align="right">{formatNumber(comparison.difference)}</TableCell>
                  <TableCell align="right">{formatNumber(effectSize.value)}</TableCell>
                  <TableCell>{effectSize.interpretation || "—"}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </Box>
  );
}

function renderGroupComparisonSection(section) {
  const result = section.result || {};
  const test = result.test || {};
  const effectSize = result.effect_size;

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Метод: ${result.method_name || result.method || "—"}`} />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Групп: ${formatNumber(result.n_groups)}`} />
        <Chip label={`α: ${formatNumber(result.alpha)}`} />
        <Chip label={`Статистика критерия: ${formatNumber(test.statistic)}`} />
        <Chip label={`p-value: ${formatNumber(test.p_value)}`} />
        <Chip label={`Статистически значимо: ${test.significant ? "да" : "нет"}`} />
      </Stack>

      <Typography color="text.secondary" variant="body2">
        {test.interpretation || "—"}
      </Typography>

      {effectSize && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip label={`Размер эффекта: ${effectSize.type}`} />
          <Chip label={`Значение: ${formatNumber(effectSize.value)}`} />
          <Chip label={effectSize.interpretation || "—"} />
        </Stack>
      )}

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <GroupComparisonMeanChart result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Группы
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Группа</TableCell>
              <TableCell align="right">n</TableCell>
              <TableCell align="right">Среднее</TableCell>
              <TableCell align="right">Медиана</TableCell>
              <TableCell align="right">Стандартное отклонение</TableCell>
              <TableCell align="right">Мин</TableCell>
              <TableCell align="right">Макс</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(result.groups || []).map((group) => (
              <TableRow key={String(group.group)}>
                <TableCell>{group.label || group.group}</TableCell>
                <TableCell align="right">{formatNumber(group.n)}</TableCell>
                <TableCell align="right">{formatNumber(group.mean)}</TableCell>
                <TableCell align="right">{formatNumber(group.median)}</TableCell>
                <TableCell align="right">{formatNumber(group.std)}</TableCell>
                <TableCell align="right">{formatNumber(group.min)}</TableCell>
                <TableCell align="right">{formatNumber(group.max)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      {renderPostHocComparisons(result.post_hoc)}
    </Stack>
  );
}

function renderTimeDistributionTable(title, rows) {
  if (!rows?.length) return null;
  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        {title}
      </Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Интервал</TableCell>
            <TableCell align="right">Частота</TableCell>
            <TableCell align="right">Доля</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((item) => (
            <TableRow key={`${title}-${item.label}`}>
              <TableCell>{item.label}</TableCell>
              <TableCell align="right">{formatNumber(item.count)}</TableCell>
              <TableCell align="right">{formatNumber(item.percent)}%</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

function renderTimeAnalysisSection(section) {
  const result = section.result || {};
  const summary = result.summary || {};
  const groupTimeTest = result.group_time_test;
  const summaryRows = [
    ["total_started", summary.total_started],
    ["total_finished", summary.total_finished],
    ["total_completed", summary.total_completed],
    ["total_screened_out", summary.total_screened_out],
    ["total_active_unfinished", summary.total_active_unfinished],
    ["completion_rate", `${formatNumber(summary.completion_rate)}%`],
    ["screenout_rate", `${formatNumber(summary.screenout_rate)}%`],
    ["finish_rate", `${formatNumber(summary.finish_rate)}%`],
    ["average_completion_time_seconds", formatDurationSeconds(summary.average_completion_time_seconds)],
    ["median_completion_time_seconds", formatDurationSeconds(summary.median_completion_time_seconds)],
    ["min_completion_time_seconds", formatDurationSeconds(summary.min_completion_time_seconds)],
    ["max_completion_time_seconds", formatDurationSeconds(summary.max_completion_time_seconds)],
    ["average_screenout_time_seconds", formatDurationSeconds(summary.average_screenout_time_seconds)],
    ["median_screenout_time_seconds", formatDurationSeconds(summary.median_screenout_time_seconds)],
    ["min_screenout_time_seconds", formatDurationSeconds(summary.min_screenout_time_seconds)],
    ["max_screenout_time_seconds", formatDurationSeconds(summary.max_screenout_time_seconds)],
  ];

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Начали: ${formatNumber(summary.total_started)}`} />
        <Chip label={`Полностью завершили: ${formatNumber(summary.total_completed)}`} />
        <Chip label={`Отсеяны: ${formatNumber(summary.total_screened_out)}`} />
        <Chip label={`Доля полных завершений: ${formatNumber(summary.completion_rate)}%`} />
        <Chip label={`Доля отсева: ${formatNumber(summary.screenout_rate)}%`} />
        <Chip label={`Среднее время прохождения: ${formatDurationSeconds(summary.average_completion_time_seconds)}`} />
        <Chip label={`Среднее время до отсева: ${formatDurationSeconds(summary.average_screenout_time_seconds)}`} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <TimeDistributionChart
        data={result.completion_time_distribution || []}
        title="Распределение времени завершения"
      />
      <TimeDistributionChart
        data={result.screenout_time_distribution || []}
        title="Распределение времени до отсева"
      />
      <TimeScreenoutReasonsChart result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Сводные показатели
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Показатель</TableCell>
              <TableCell align="right">Значение</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {summaryRows.map(([label, value]) => (
              <TableRow key={label}>
                <TableCell>{TIME_SUMMARY_LABELS[label] || label}</TableCell>
                <TableCell align="right">{value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      {renderTimeDistributionTable("Распределение времени полного прохождения", result.completion_time_distribution || [])}
      {renderTimeDistributionTable("Распределение времени до отсева", result.screenout_time_distribution || [])}

      {!!(result.screenout_reasons || []).length && (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Причины отсева
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Причина</TableCell>
                <TableCell align="right">Количество</TableCell>
                <TableCell align="right">% от отсеянных</TableCell>
                <TableCell align="right">Среднее время до отсева</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(result.screenout_reasons || []).map((reason) => (
                <TableRow key={reason.reason}>
                  <TableCell>{reason.reason}</TableCell>
                  <TableCell align="right">{formatNumber(reason.count)}</TableCell>
                  <TableCell align="right">{formatNumber(reason.percent_screened_out)}%</TableCell>
                  <TableCell align="right">{formatDurationSeconds(reason.average_time_to_screenout_seconds)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      {!!(result.group_breakdown || []).length && (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Разбивка по группам
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Группа</TableCell>
                <TableCell align="right">Начали</TableCell>
                <TableCell align="right">Полностью завершили</TableCell>
                <TableCell align="right">Отсеяны</TableCell>
                <TableCell align="right">Доля полных завершений</TableCell>
                <TableCell align="right">Доля отсева</TableCell>
                <TableCell align="right">Медианное время прохождения</TableCell>
                <TableCell align="right">Медианное время до отсева</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(result.group_breakdown || []).map((group) => (
                <TableRow key={String(group.group)}>
                  <TableCell>{group.group_label || group.group}</TableCell>
                  <TableCell align="right">{formatNumber(group.total_started)}</TableCell>
                  <TableCell align="right">{formatNumber(group.total_completed)}</TableCell>
                  <TableCell align="right">{formatNumber(group.total_screened_out)}</TableCell>
                  <TableCell align="right">{formatNumber(group.completion_rate)}%</TableCell>
                  <TableCell align="right">{formatNumber(group.screenout_rate)}%</TableCell>
                  <TableCell align="right">{formatDurationSeconds(group.completion_time?.median)}</TableCell>
                  <TableCell align="right">{formatDurationSeconds(group.screenout_time?.median)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      {groupTimeTest && (
        <Stack spacing={1}>
          <Typography variant="subtitle1">Критерий различий времени между группами</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={`Метод: ${groupTimeTest.method || "—"}`} />
            <Chip label={`Статистика критерия: ${formatNumber(groupTimeTest.statistic)}`} />
            <Chip label={`p-value: ${formatNumber(groupTimeTest.p_value)}`} />
            <Chip label={`Статистически значимо: ${groupTimeTest.significant ? "да" : "нет"}`} />
          </Stack>
          <Typography color="text.secondary" variant="body2">
            {groupTimeTest.interpretation || "—"}
          </Typography>
        </Stack>
      )}
    </Stack>
  );
}

function renderReliabilityAnalysisSection(section) {
  const result = section.result || {};
  const variables = result.variables || [];
  const matrix = result.inter_item_correlation_matrix || [];

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label="Метод: α Кронбаха" />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Пунктов: ${formatNumber(result.n_items)}`} />
        <Chip label={`α Кронбаха: ${formatNumber(result.alpha)}`} />
        <Chip label={`Стандартизованная α: ${formatNumber(result.standardized_alpha)}`} />
        <Chip label={result.interpretation || "—"} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <ReliabilityItemChart result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Статистики пунктов
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Пункт</TableCell>
              <TableCell align="right">Среднее</TableCell>
              <TableCell align="right">Дисперсия</TableCell>
              <TableCell align="right">Стандартное отклонение</TableCell>
              <TableCell align="right">Корреляция пункта с суммарной шкалой</TableCell>
              <TableCell align="right">α при удалении пункта</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(result.item_statistics || []).map((item) => (
              <TableRow key={item.code}>
                <TableCell>{item.label || item.code}</TableCell>
                <TableCell align="right">{formatNumber(item.mean)}</TableCell>
                <TableCell align="right">{formatNumber(item.variance)}</TableCell>
                <TableCell align="right">{formatNumber(item.std)}</TableCell>
                <TableCell align="right">{formatNumber(item.item_total_correlation)}</TableCell>
                <TableCell align="right">{formatNumber(item.alpha_if_deleted)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Межпунктовые корреляции
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Пункт</TableCell>
              {variables.map((variable) => (
                <TableCell key={variable.code} align="right">
                  {variable.label || variable.code}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {variables.map((variable, rowIndex) => (
              <TableRow key={variable.code}>
                <TableCell>{variable.label || variable.code}</TableCell>
                {variables.map((column, columnIndex) => (
                  <TableCell key={column.code} align="right">
                    {formatNumber(matrix[rowIndex]?.[columnIndex])}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Stack>
  );
}

function renderScaleIndexSection(section) {
  const result = section.result || {};
  const summary = result.score_summary || {};
  const reliability = result.reliability || {};
  const summaryRows = [
    ["n", summary.n],
    ["mean", summary.mean],
    ["median", summary.median],
    ["std", summary.std],
    ["variance", summary.variance],
    ["min", summary.min],
    ["max", summary.max],
    ["p25", summary.p25],
    ["p75", summary.p75],
    ["iqr", summary.iqr],
  ];
  const scores = (result.scores || []).slice(0, 20);

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Метод: ${result.method || "scale_index"}`} />
        <Chip label={`Рассчитано индексов: ${formatNumber(result.n_scored)}`} />
        <Chip label={`Пунктов: ${formatNumber(result.n_items)}`} />
        <Chip label={`Способ расчета: ${result.calculation || "—"}`} />
        <Chip label={`α Кронбаха: ${formatNumber(reliability.alpha)}`} />
        <Chip label={reliability.interpretation || "—"} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}
      {(reliability.warnings || []).map((warning) => (
        <Alert key={`reliability-${warning}`} severity="warning">{warning}</Alert>
      ))}

      <ScaleIndexDistributionChart result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Сводка индекса
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Показатель</TableCell>
              <TableCell align="right">Значение</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {summaryRows.map(([label, value]) => (
              <TableRow key={label}>
                <TableCell>{SCALE_SUMMARY_LABELS[label] || label}</TableCell>
                <TableCell align="right">{formatNumber(value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Статистики пунктов
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Пункт</TableCell>
              <TableCell align="center">Обратное кодирование</TableCell>
              <TableCell align="right">n</TableCell>
              <TableCell align="right">Пропуски</TableCell>
              <TableCell align="right">Среднее</TableCell>
              <TableCell align="right">Стандартное отклонение</TableCell>
              <TableCell align="right">Мин</TableCell>
              <TableCell align="right">Макс</TableCell>
              <TableCell align="right">Корреляция пункта с суммарной шкалой</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(result.item_statistics || []).map((item) => (
              <TableRow key={item.code}>
                <TableCell>{item.label || item.code}</TableCell>
                <TableCell align="center">{item.reverse ? "да" : "нет"}</TableCell>
                <TableCell align="right">{formatNumber(item.n)}</TableCell>
                <TableCell align="right">{formatNumber(item.missing)}</TableCell>
                <TableCell align="right">{formatNumber(item.mean)}</TableCell>
                <TableCell align="right">{formatNumber(item.std)}</TableCell>
                <TableCell align="right">{formatNumber(item.min)}</TableCell>
                <TableCell align="right">{formatNumber(item.max)}</TableCell>
                <TableCell align="right">{formatNumber(item.item_total_correlation)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Надежность
        </Typography>
        {result.reliability ? (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={`α Кронбаха: ${formatNumber(reliability.alpha)}`} />
            <Chip label={`Стандартизованная α: ${formatNumber(reliability.standardized_alpha)}`} />
            <Chip label={`Средняя межпунктовая корреляция: ${formatNumber(reliability.mean_inter_item_correlation)}`} />
            <Chip label={reliability.interpretation || "—"} />
          </Stack>
        ) : (
          <Typography color="text.secondary">α Кронбаха не рассчитана.</Typography>
        )}
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Распределение значений индекса
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Интервал</TableCell>
              <TableCell align="right">Частота</TableCell>
              <TableCell align="right">Доля</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(result.score_distribution || []).map((item) => (
              <TableRow key={item.label}>
                <TableCell>{item.label}</TableCell>
                <TableCell align="right">{formatNumber(item.count)}</TableCell>
                <TableCell align="right">{formatNumber(item.percent)}%</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Alert severity="info">
        В интерфейсе показаны первые 20 индивидуальных значений индекса. Полная таблица доступна в CSV/XLSX.
      </Alert>
      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID ответа</TableCell>
              <TableCell align="right">Значение индекса</TableCell>
              <TableCell align="right">Отвеченных пунктов</TableCell>
              <TableCell align="right">Пропущенных пунктов</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {scores.map((score) => (
              <TableRow key={score.response_id}>
                <TableCell>{score.response_id}</TableCell>
                <TableCell align="right">{formatNumber(score.score)}</TableCell>
                <TableCell align="right">{formatNumber(score.answered_items)}</TableCell>
                <TableCell align="right">{formatNumber(score.missing_items)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Stack>
  );
}

function renderMissingShortTable(title, rows, helperText = "") {
  if (!rows?.length) return null;

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        {title}
      </Typography>
      {helperText && (
        <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
          {helperText}
        </Typography>
      )}
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Вопрос</TableCell>
            <TableCell align="right">Видели</TableCell>
            <TableCell align="right">Пропустили</TableCell>
            <TableCell align="right">Доля пропусков среди показанных</TableCell>
            <TableCell align="right">Доля видимости</TableCell>
            <TableCell>Тип пропуска</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((item) => (
            <TableRow key={`${title}-${item.question_id}`}>
              <TableCell>{item.label || item.question_id}</TableCell>
              <TableCell align="right">{formatNumber(item.shown_count)}</TableCell>
              <TableCell align="right">{formatNumber(item.skipped_count)}</TableCell>
              <TableCell align="right">{formatNumber(item.skip_rate_shown)}%</TableCell>
              <TableCell align="right">{formatNumber(item.visibility_rate)}%</TableCell>
              <TableCell>{item.missing_type || "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

function renderMissingAnalysisSection(section) {
  const result = section.result || {};
  const summary = result.summary || {};
  const screenedOut = result.screened_out_context;
  const summaryRows = [
    ["total_shown_slots", summary.total_shown_slots],
    ["total_answered_slots", summary.total_answered_slots],
    ["total_skipped_slots", summary.total_skipped_slots],
    ["total_not_shown_slots", summary.total_not_shown_slots],
    ["overall_skip_rate_shown", `${formatNumber(summary.overall_skip_rate_shown)}%`],
    ["overall_visibility_rate", `${formatNumber(summary.overall_visibility_rate)}%`],
  ];

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Завершили без отсева: ${formatNumber(summary.total_completed_normal)}`} />
        <Chip label={`Вопросов: ${formatNumber(summary.questions_count)}`} />
        <Chip label={`Общая доля пропусков среди показанных: ${formatNumber(summary.overall_skip_rate_shown)}%`} />
        <Chip label={`Вопросов с высокой долей пропусков: ${formatNumber(summary.questions_with_high_missing)}`} />
        <Chip label={`Вопросов с низкой видимостью: ${formatNumber(summary.questions_with_low_visibility)}`} />
      </Stack>

      <Alert severity="info">
        Структурные пропуски из-за ветвления не считаются реальными пропусками.
      </Alert>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <MissingAnalysisChart result={result} />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Сводные показатели
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Показатель</TableCell>
              <TableCell align="right">Значение</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {summaryRows.map(([label, value]) => (
              <TableRow key={label}>
                <TableCell>{MISSING_SUMMARY_LABELS[label] || label}</TableCell>
                <TableCell align="right">{value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Вопросы
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Вопрос</TableCell>
              <TableCell>Тип</TableCell>
              <TableCell>Обязательный</TableCell>
              <TableCell align="right">Видели</TableCell>
              <TableCell align="right">Не видели из-за ветвления</TableCell>
              <TableCell align="right">Ответили</TableCell>
              <TableCell align="right">Пропустили</TableCell>
              <TableCell align="right">Доля пропусков среди показанных</TableCell>
              <TableCell align="right">Доля видимости</TableCell>
              <TableCell>Интерпретация</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(result.questions || []).map((item) => (
              <TableRow key={item.question_id}>
                <TableCell>{item.label || item.question_id}</TableCell>
                <TableCell>{item.qtype}</TableCell>
                <TableCell>{item.required ? "да" : "нет"}</TableCell>
                <TableCell align="right">{formatNumber(item.shown_count)}</TableCell>
                <TableCell align="right">{formatNumber(item.not_shown_count)}</TableCell>
                <TableCell align="right">{formatNumber(item.answered_count)}</TableCell>
                <TableCell align="right">{formatNumber(item.skipped_count)}</TableCell>
                <TableCell align="right">{formatNumber(item.skip_rate_shown)}%</TableCell>
                <TableCell align="right">{formatNumber(item.visibility_rate)}%</TableCell>
                <TableCell>{item.interpretation || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      {renderMissingShortTable("Вопросы с наибольшей долей пропусков", result.top_skipped_questions || [])}
      {renderMissingShortTable(
        "Вопросы с низкой видимостью",
        result.low_visibility_questions || [],
        "Это не обязательно проблема качества, часто связано с ветвлением.",
      )}

      {!!(result.never_shown_questions || []).length && (
        <Alert severity="warning">
          Некоторые вопросы не были показаны ни одному завершившему респонденту. Проверьте условия ветвления.
        </Alert>
      )}
      {renderMissingShortTable("Вопросы, ни разу не показанные респондентам", result.never_shown_questions || [])}

      {!!(result.required_questions_with_missing || []).length && (
        <Alert severity="warning">
          Есть обязательные вопросы с реальными пропусками среди респондентов, которым вопрос был показан.
        </Alert>
      )}
      {renderMissingShortTable("Обязательные вопросы с пропусками", result.required_questions_with_missing || [])}

      {!!(result.groups || []).length && (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Сводка по группам
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Группа</TableCell>
                <TableCell align="right">Показано вопросов</TableCell>
                <TableCell align="right">Получено ответов</TableCell>
                <TableCell align="right">Пропущено показанных вопросов</TableCell>
                <TableCell align="right">Доля пропусков среди показанных</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(result.groups || []).map((group) => (
                <TableRow key={String(group.group)}>
                  <TableCell>{group.group_label || group.group}</TableCell>
                  <TableCell align="right">{formatNumber(group.total_shown_slots)}</TableCell>
                  <TableCell align="right">{formatNumber(group.total_answered_slots)}</TableCell>
                  <TableCell align="right">{formatNumber(group.total_skipped_slots)}</TableCell>
                  <TableCell align="right">{formatNumber(group.overall_skip_rate_shown)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      {screenedOut && (
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Контекст отсева
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
            <Chip label={`Отсеяны: ${formatNumber(screenedOut.total_screened_out)}`} />
            <Chip label={`Среднее число увиденных вопросов до отсева: ${formatNumber(screenedOut.average_seen_questions_before_screenout)}`} />
          </Stack>
          <Typography color="text.secondary" variant="body2">
            {screenedOut.note}
          </Typography>
        </Box>
      )}
    </Stack>
  );
}

function renderSection(section) {
  if (section.error) {
    return <Alert severity="error">{section.error}</Alert>;
  }

  if (section.type === "correlation") return renderCorrelationSection(section);
  if (section.type === "crosstab") return renderCrosstabSection(section);
  if (section.type === "chi_square") return renderChiSquareSection(section);
  if (section.type === "correspondence_analysis") return renderCorrespondenceAnalysisSection(section);
  if (section.type === "regression") return renderRegressionSection(section);
  if (section.type === "logistic_regression") return renderLogisticRegressionSection(section);
  if (section.type === "factor_analysis") return renderFactorAnalysisSection(section);
  if (section.type === "cluster_analysis") return renderClusterAnalysisSection(section);
  if (section.type === "group_comparison") return renderGroupComparisonSection(section);
  if (section.type === "time_analysis") return renderTimeAnalysisSection(section);
  if (section.type === "reliability_analysis") return renderReliabilityAnalysisSection(section);
  if (section.type === "scale_index") return renderScaleIndexSection(section);
  if (section.type === "missing_analysis") return renderMissingAnalysisSection(section);

  return <Typography color="text.secondary">Неизвестный тип секции.</Typography>;
}

export default function ReportResultPage() {
  const { id, reportId } = useParams();
  const navigate = useNavigate();
  const [serverCharts, setServerCharts] = useState({});
  const serverChartsRef = useRef({});

  const { report, storedReport, isLoading, error } = useStoredReport(reportId);
  const reportTitle = storedReport?.title || report?.title;
  const surveyTitle = storedReport?.survey?.title || report?.survey_title;
  const generatedAt = storedReport?.generatedAt || report?.created_at;
  const sections = storedReport?.sections || [];

  useEffect(() => {
    serverChartsRef.current = serverCharts;
  }, [serverCharts]);

  useEffect(() => () => {
    Object.values(serverChartsRef.current).forEach((item) => {
      if (item?.url) URL.revokeObjectURL(item.url);
    });
  }, []);

  async function handleRequestChart(section) {
    const sectionId = section.id;
    if (!sectionId) return;

    setServerCharts((current) => ({
      ...current,
      [sectionId]: {
        ...(current[sectionId] || {}),
        loading: true,
        error: "",
      },
    }));

    try {
      const blob = await fetchReportMatplotlibChart(reportId, {
        section_id: sectionId,
        chart_type: "auto",
      });
      const url = URL.createObjectURL(blob);

      setServerCharts((current) => {
        const oldUrl = current[sectionId]?.url;
        if (oldUrl) URL.revokeObjectURL(oldUrl);

        return {
          ...current,
          [sectionId]: {
            loading: false,
            error: "",
            url,
          },
        };
      });
    } catch (chartError) {
      setServerCharts((current) => ({
        ...current,
        [sectionId]: {
          ...(current[sectionId] || {}),
          loading: false,
          error: chartError.message || "Не удалось построить график",
        },
      }));
    }
  }

  if (isLoading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Alert severity="error">Не удается загрузить отчёт</Alert>;
  }

  if (!storedReport) {
    return (
      <Alert severity="warning">Результат отчёта не найден</Alert>
    );
  }

  if (!report) {
    return (
      <Container maxWidth={false} sx={{ mt: 4, width: "100%" }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Результат отчёта не найден
        </Alert>
        <Button
          variant="contained"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/analytics/surveys/${id}/report-builder`)}
        >
          Вернуться в конструктор
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth={false} sx={{ mt: 4, width: "100%" }}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 1 }}>
            {reportTitle}
          </Typography>
          <Typography color="text.secondary">
            {surveyTitle} · {formatDate(generatedAt)}
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/analytics/surveys/${id}/report-builder`)}
        >
          Назад в конструктор
        </Button>
      </Stack>

      <Stack spacing={3}>
        {sections.map((section, index) => (
          <ReportSectionCard
            key={section.id || index}
            section={section}
            onRequestChart={handleRequestChart}
            serverChart={serverCharts[section.id]}
          >
            {renderSection(section)}
          </ReportSectionCard>
        ))}
      </Stack>
    </Container>
  );
}
