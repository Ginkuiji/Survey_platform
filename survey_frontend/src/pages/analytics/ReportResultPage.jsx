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
  regression: "Линейная регрессия",
  factor_analysis: "Факторный анализ",
  cluster_analysis: "Кластерный анализ",
};

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (typeof value !== "number") return String(value);
  return Number.isInteger(value) ? String(value) : value.toFixed(4);
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "вЂ”";
  return `${(Number(value) * 100).toFixed(2)}%`;
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

function renderFactorAnalysisSection(section) {
  const result = section.result || {};
  const explainedVariance = result.explained_variance || [];
  const loadings = result.loadings || [];
  const eigenvalues = result.eigenvalues || [];
  const factorNames = explainedVariance.map(item => item.factor);

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Method: ${result.method || "вЂ”"}`} />
        <Chip label={`n: ${formatNumber(result.n)}`} />
        <Chip label={`Variables: ${formatNumber(result.n_variables)}`} />
        <Chip label={`Factors: ${formatNumber(result.n_factors)}`} />
        <Chip label={`Rotation: ${result.rotation || "вЂ”"}`} />
        <Chip label={`Cumulative: ${formatPercent(result.cumulative_explained_variance)}`} />
      </Stack>

      {(result.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

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
    </Stack>
  );
}

function renderClusterAnalysisSection(section) {
  const result = section.result || {};
  const variables = result.variables || [];
  const clusters = result.clusters || [];

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
  if (section.type === "regression") return renderRegressionSection(section);
  if (section.type === "factor_analysis") return renderFactorAnalysisSection(section);
  if (section.type === "cluster_analysis") return renderClusterAnalysisSection(section);

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
