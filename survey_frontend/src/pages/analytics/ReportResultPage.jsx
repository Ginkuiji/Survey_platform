import { useMemo } from "react";
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
import { fetchAnalysisReportById } from "../../api/analytics";

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
        <Chip label={`Dataset: ${result?.dataset_size ?? "—"}`} />
      </Stack>

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
                    row {formatNumber(column.percent_row)}% · total {formatNumber(column.percent_total)}%
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
  return renderCrosstabTable(section.result?.crosstab);
}

function renderExpectedTable(expected) {
  if (!expected?.length) {
    return <Typography color="text.secondary">Expected values недоступны.</Typography>;
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
      {renderCrosstabTable(section.result?.crosstab)}

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`χ²: ${formatNumber(chiSquare?.chi2)}`} />
        <Chip label={`p-value: ${formatNumber(chiSquare?.p_value)}`} />
        <Chip label={`dof: ${formatNumber(chiSquare?.dof)}`} />
        <Chip label={`Cramér’s V: ${formatNumber(cramersV?.cramers_v)}`} />
        <Chip label={`Сила связи: ${cramersV?.interpretation || "—"}`} />
        <Chip label={`n: ${formatNumber(cramersV?.n)}`} />
        <Chip label={`${formatNumber(cramersV?.rows)}×${formatNumber(cramersV?.columns)}`} />
      </Stack>

      <Typography color="text.secondary" variant="body2">
        Cramér’s V показывает силу связи между категориальными переменными от 0 до 1.
      </Typography>

      <Box>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Expected values
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
            <TableCell align="right">Mass</TableCell>
            {dimensionNames.map((dimension) => (
              <TableCell key={dimension} align="right">{dimension}</TableCell>
            ))}
            {dimensionNames.map((dimension) => (
              <TableCell key={`${dimension}-contribution`} align="right">Contribution {dimension}</TableCell>
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
        <Chip label={`Total inertia: ${formatNumber(result.total_inertia)}`} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <Box>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Таблица сопряжённости
        </Typography>
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
              <TableCell align="right">Eigenvalue</TableCell>
              <TableCell align="right">Explained inertia</TableCell>
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
        <Chip label={`Target: ${getVariableLabel(result, result?.target)}`} />
        <Chip label={`n: ${formatNumber(result?.n)}`} />
        <Chip label={`Features: ${featureLabels.length}`} />
        <Chip label={`R²: ${formatNumber(result?.r2)}`} />
        <Chip label={`Adjusted R²: ${formatNumber(result?.adjusted_r2)}`} />
      </Stack>

      <Typography color="text.secondary" variant="body2">
        Features: {(result?.features || []).map(code => getVariableLabel(result, code)).join(", ") || "—"}
      </Typography>

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
        <Chip label={`Method: ${result.method || "—"}`} />
        <Chip label={`Target: ${getVariableLabel(result, result.target)}`} />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Positive: ${formatNumber(result.positive_class_count)}`} />
        <Chip label={`Negative: ${formatNumber(result.negative_class_count)}`} />
        <Chip label={`Threshold: ${formatNumber(result.threshold)}`} />
        <Chip label={`Accuracy: ${formatNumber(metrics.accuracy)}`} />
        <Chip label={`Precision: ${formatNumber(metrics.precision)}`} />
        <Chip label={`Recall: ${formatNumber(metrics.recall)}`} />
        <Chip label={`F1: ${formatNumber(metrics.f1)}`} />
        <Chip label={`McFadden R²: ${formatNumber(metrics.mcfadden_r2)}`} />
      </Stack>

      <Typography color="text.secondary" variant="body2">
        Features: {featureLabels.join(", ") || "—"}
      </Typography>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}
      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Confusion matrix
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell />
              <TableCell align="right">Predicted 0</TableCell>
              <TableCell align="right">Predicted 1</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell>Actual 0</TableCell>
              <TableCell align="right">{formatNumber(confusionMatrix.tn)}</TableCell>
              <TableCell align="right">{formatNumber(confusionMatrix.fp)}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Actual 1</TableCell>
              <TableCell align="right">{formatNumber(confusionMatrix.fn)}</TableCell>
              <TableCell align="right">{formatNumber(confusionMatrix.tp)}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Coefficients
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Переменная</TableCell>
              <TableCell align="right">Coefficient</TableCell>
              <TableCell align="right">Odds ratio</TableCell>
              <TableCell>Interpretation</TableCell>
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
        Predictions are stored in the API result; this view shows model summary only.
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
        <Chip label={`Method: ${result.method || "вЂ”"}`} />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Variables: ${formatNumber(result.n_variables)}`} />
        <Chip label={`Factors: ${formatNumber(result.n_factors)}`} />
        <Chip label={`Rotation: ${result.rotation || "вЂ”"}`} />
        <Chip label={`Cumulative: ${formatPercent(result.cumulative_explained_variance)}`} />
        <Chip label={`KMO: ${formatNumber(kmo.overall)}`} />
        <Chip label={`Bartlett p: ${formatNumber(bartlett.p_value)}`} />
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

      <Box>
        <Typography variant="subtitle1">Рекомендация числа факторов</Typography>
        <Typography color="text.secondary" variant="body2">
          {recommendations.message || "—"}
        </Typography>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>KMO</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
          <Chip label={`Overall: ${formatNumber(kmo.overall)}`} />
          <Chip label={kmo.interpretation || "—"} />
        </Stack>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Variable</TableCell>
              <TableCell align="right">KMO</TableCell>
              <TableCell>Interpretation</TableCell>
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
        <Typography variant="subtitle1">Bartlett&apos;s test</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ my: 1 }}>
          <Chip label={`chi-square: ${formatNumber(bartlett.chi_square)}`} />
          <Chip label={`dof: ${formatNumber(bartlett.dof)}`} />
          <Chip label={`p-value: ${formatNumber(bartlett.p_value)}`} />
          <Chip label={`Significant: ${bartlett.significant === null || bartlett.significant === undefined ? "—" : (bartlett.significant ? "да" : "нет")}`} />
        </Stack>
        <Typography color="text.secondary" variant="body2">
          {bartlett.interpretation || "—"}
        </Typography>
      </Box>

      {scree.length > 0 && (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>Scree data</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Component</TableCell>
                <TableCell align="right">Eigenvalue</TableCell>
                <TableCell align="right">Explained variance</TableCell>
                <TableCell align="right">Cumulative</TableCell>
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
          Explained variance
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Factor</TableCell>
              <TableCell align="right">Value</TableCell>
              <TableCell align="right">Percent</TableCell>
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
          Loadings
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Variable</TableCell>
              <TableCell align="right">Communality</TableCell>
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
          Eigenvalues
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Component</TableCell>
              <TableCell align="right">Eigenvalue</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {eigenvalues.map((value, index) => (
              <TableRow key={index}>
                <TableCell>Component {index + 1}</TableCell>
                <TableCell align="right">{formatNumber(value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      {factorScores.length > 0 && (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <Alert severity="info" sx={{ mb: 1 }}>
            Factor scores рассчитаны; в интерфейсе показаны первые 20.
          </Alert>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>response_id</TableCell>
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
        <Chip label={`Method: ${result.method || "—"}`} />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Variables: ${formatNumber(result.n_variables)}`} />
        <Chip label={`Clusters: ${formatNumber(result.n_clusters)}`} />
        <Chip label={`Standardize: ${result.standardize ? "yes" : "no"}`} />
        <Chip label={`Inertia: ${formatNumber(result.inertia)}`} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Cluster</TableCell>
              <TableCell align="right">Size</TableCell>
              <TableCell align="right">Percent</TableCell>
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
        Assignments are stored in the result for export/API use; this view shows cluster summary only.
      </Typography>

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
        Post-hoc сравнения
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
              <TableCell align="right">Statistic</TableCell>
              <TableCell align="right">p-value</TableCell>
              <TableCell align="right">p adjusted</TableCell>
              <TableCell>Significant</TableCell>
              <TableCell align="right">Difference</TableCell>
              <TableCell align="right">Effect size</TableCell>
              <TableCell>Interpretation</TableCell>
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
        <Chip label={`alpha: ${formatNumber(result.alpha)}`} />
        <Chip label={`statistic: ${formatNumber(test.statistic)}`} />
        <Chip label={`p-value: ${formatNumber(test.p_value)}`} />
        <Chip label={`Статистически значимо: ${test.significant ? "да" : "нет"}`} />
      </Stack>

      <Typography color="text.secondary" variant="body2">
        {test.interpretation || "—"}
      </Typography>

      {effectSize && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip label={`Effect size: ${effectSize.type}`} />
          <Chip label={`value: ${formatNumber(effectSize.value)}`} />
          <Chip label={effectSize.interpretation || "—"} />
        </Stack>
      )}

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

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
              <TableCell align="right">Std</TableCell>
              <TableCell align="right">Min</TableCell>
              <TableCell align="right">Max</TableCell>
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
            <TableCell align="right">Count</TableCell>
            <TableCell align="right">Percent</TableCell>
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
        <Chip label={`Started: ${formatNumber(summary.total_started)}`} />
        <Chip label={`Completed: ${formatNumber(summary.total_completed)}`} />
        <Chip label={`Screened out: ${formatNumber(summary.total_screened_out)}`} />
        <Chip label={`Completion rate: ${formatNumber(summary.completion_rate)}%`} />
        <Chip label={`Screenout rate: ${formatNumber(summary.screenout_rate)}%`} />
        <Chip label={`Avg completion: ${formatDurationSeconds(summary.average_completion_time_seconds)}`} />
        <Chip label={`Avg screenout: ${formatDurationSeconds(summary.average_screenout_time_seconds)}`} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Summary
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
                <TableCell>{label}</TableCell>
                <TableCell align="right">{value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      {renderTimeDistributionTable("Completion time distribution", result.completion_time_distribution || [])}
      {renderTimeDistributionTable("Screenout time distribution", result.screenout_time_distribution || [])}

      {!!(result.screenout_reasons || []).length && (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Screenout reasons
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Причина</TableCell>
                <TableCell align="right">Количество</TableCell>
                <TableCell align="right">% от screened out</TableCell>
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
            Group breakdown
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Группа</TableCell>
                <TableCell align="right">Started</TableCell>
                <TableCell align="right">Completed</TableCell>
                <TableCell align="right">Screened out</TableCell>
                <TableCell align="right">Completion rate</TableCell>
                <TableCell align="right">Screenout rate</TableCell>
                <TableCell align="right">Median completion</TableCell>
                <TableCell align="right">Median screenout</TableCell>
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
          <Typography variant="subtitle1">Group time test</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={`Method: ${groupTimeTest.method || "—"}`} />
            <Chip label={`Statistic: ${formatNumber(groupTimeTest.statistic)}`} />
            <Chip label={`p-value: ${formatNumber(groupTimeTest.p_value)}`} />
            <Chip label={`Significant: ${groupTimeTest.significant ? "да" : "нет"}`} />
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
        <Chip label="Метод: Cronbach’s alpha" />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`items: ${formatNumber(result.n_items)}`} />
        <Chip label={`alpha: ${formatNumber(result.alpha)}`} />
        <Chip label={`standardized alpha: ${formatNumber(result.standardized_alpha)}`} />
        <Chip label={result.interpretation || "—"} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Item statistics
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Пункт</TableCell>
              <TableCell align="right">Mean</TableCell>
              <TableCell align="right">Variance</TableCell>
              <TableCell align="right">Std</TableCell>
              <TableCell align="right">Item-total correlation</TableCell>
              <TableCell align="right">Alpha if deleted</TableCell>
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
          Inter-item correlations
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

  return <Typography color="text.secondary">Неизвестный тип секции.</Typography>;
}

export default function ReportResultPage() {
  const { id, reportId } = useParams();
  const navigate = useNavigate();

  const { report, storedReport, isLoading, error } = useStoredReport(reportId);
  const reportTitle = storedReport?.title || report?.title;
  const surveyTitle = storedReport?.survey?.title || report?.survey_title;
  const generatedAt = storedReport?.generatedAt || report?.created_at;
  const sections = storedReport?.sections || [];

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
          <Card key={section.id || index}>
            <CardContent>
              <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1} sx={{ mb: 2 }}>
                <Box>
                  <Typography variant="h6">
                    {section.title}
                  </Typography>
                  <Typography color="text.secondary" variant="body2">
                    {SECTION_LABELS[section.type] || section.type}
                  </Typography>
                </Box>
                {section.result?.analysis_type && (
                  <Chip label={section.result.analysis_type} sx={{ alignSelf: { xs: "flex-start", md: "center" } }} />
                )}
              </Stack>

              {renderSection(section)}
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
