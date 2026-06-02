import {
  Alert,
  Box,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const CHART_HEIGHT = 320;
const SMALL_CHART_HEIGHT = 240;
const MAX_BAR_ITEMS = 20;
const MAX_LABEL_LENGTH = 28;
const COLORS = ["#2f80ed", "#27ae60", "#f2c94c", "#eb5757", "#9b51e0", "#56ccf2", "#f2994a", "#219653"];

function truncateLabel(value, max = MAX_LABEL_LENGTH) {
  const label = String(value ?? "");
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

function toPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null;
  return Number(value) <= 1 ? Number(value) * 100 : Number(value);
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  if (typeof value !== "number") return String(value);
  return Number.isInteger(value) ? String(value) : value.toFixed(4);
}

function chartEmpty(message = "Нет данных для построения графика.") {
  return <Typography color="text.secondary">{message}</Typography>;
}

function ChartBox({ children, minWidth = 640, height = CHART_HEIGHT, note = "" }) {
  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Box sx={{ minWidth, height }}>
        {children}
      </Box>
      {note && (
        <Typography color="text.secondary" variant="body2" sx={{ mt: 1 }}>
          {note}
        </Typography>
      )}
    </Box>
  );
}

function topItems(items, limit = MAX_BAR_ITEMS) {
  const safeItems = Array.isArray(items) ? items : [];
  return {
    data: safeItems.slice(0, limit),
    note: safeItems.length > limit ? `Показаны первые ${limit} элементов.` : "",
  };
}

function getVariableLabel(result, code) {
  if (!code) return "—";
  if (code === "intercept") return "Свободный член";
  return result?.variables_by_code?.[code]?.label || code;
}

function heatColor(value, mode = "signed") {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) return "transparent";
  const intensity = Math.min(Math.abs(numericValue), 1);
  if (mode === "absolute") return `rgba(47, 128, 237, ${0.08 + intensity * 0.46})`;
  if (numericValue > 0) return `rgba(39, 174, 96, ${0.08 + intensity * 0.48})`;
  if (numericValue < 0) return `rgba(235, 87, 87, ${0.08 + intensity * 0.48})`;
  return "rgba(0, 0, 0, 0.04)";
}

function axisTick({ x, y, payload }) {
  return (
    <g transform={`translate(${x},${y})`}>
      <text x={0} y={0} dy={16} textAnchor="end" fill="#666" transform="rotate(-35)" fontSize={12}>
        {truncateLabel(payload.value, 18)}
      </text>
    </g>
  );
}

export function CorrelationHeatmap({ result }) {
  const variables = result?.variables || [];
  const matrix = result?.matrix || [];
  const pValues = result?.p_values || [];
  const nMatrix = result?.n_matrix || [];
  if (!variables.length || !matrix.length) return chartEmpty();

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Тепловая карта корреляций</Typography>
      <Table size="small" sx={{ minWidth: Math.max(640, variables.length * 120) }}>
        <TableHead>
          <TableRow>
            <TableCell>Переменная</TableCell>
            {variables.map((variable) => (
              <TableCell key={variable.code} align="center">{truncateLabel(variable.label || variable.code)}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {variables.map((variable, rowIndex) => (
            <TableRow key={variable.code}>
              <TableCell component="th" scope="row">{variable.label || variable.code}</TableCell>
              {variables.map((columnVariable, columnIndex) => {
                const value = matrix[rowIndex]?.[columnIndex];
                return (
                  <TableCell
                    key={columnVariable.code}
                    align="center"
                    sx={{ backgroundColor: heatColor(value), minWidth: 96 }}
                  >
                    <Typography>{formatNumber(value)}</Typography>
                    <Typography color="text.secondary" variant="caption">
                      p={formatNumber(pValues[rowIndex]?.[columnIndex])}; n={formatNumber(nMatrix[rowIndex]?.[columnIndex])}
                    </Typography>
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

export function CorrelationScatterPlot({ result }) {
  const variables = result?.variables || [];
  const data = (result?.scatter_pairs || [])
    .map((pair) => ({ x: Number(pair.x), y: Number(pair.y) }))
    .filter((pair) => !Number.isNaN(pair.x) && !Number.isNaN(pair.y));
  if (variables.length !== 2) return null;
  if (!data.length) return chartEmpty("Нет совместных числовых наблюдений для диаграммы рассеяния.");

  return (
    <Box>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Диаграмма рассеяния</Typography>
      <ChartBox minWidth={640}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 12, right: 24, left: 8, bottom: 24 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" dataKey="x" name={variables[0]?.label || variables[0]?.code} />
            <YAxis type="number" dataKey="y" name={variables[1]?.label || variables[1]?.code} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={data} fill="#2f80ed" />
          </ScatterChart>
        </ResponsiveContainer>
      </ChartBox>
    </Box>
  );
}

function chiHeatColor(value, mode = "residual") {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) return "transparent";
  if (mode === "contribution") return `rgba(242, 153, 74, ${Math.min(0.12 + numericValue * 0.12, 0.72)})`;
  const intensity = Math.min(Math.abs(numericValue) / 3, 1);
  return numericValue >= 0
    ? `rgba(39, 174, 96, ${0.08 + intensity * 0.55})`
    : `rgba(235, 87, 87, ${0.08 + intensity * 0.55})`;
}

function ChiSquareHeatmap({ result, matrix, title, mode, helperText }) {
  const rows = result?.crosstab?.rows || [];
  const expected = result?.chi_square?.expected || [];
  if (!rows.length || !matrix?.length) return null;

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>{title}</Typography>
      {helperText && <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>{helperText}</Typography>}
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Категория</TableCell>
            {(rows[0]?.columns || []).map((column) => <TableCell key={column.value} align="center">{column.value}</TableCell>)}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={row.value}>
              <TableCell>{row.value}</TableCell>
              {(row.columns || []).map((column, columnIndex) => {
                const value = matrix[rowIndex]?.[columnIndex];
                const important = mode === "residual" && Math.abs(Number(value)) >= 2;
                return (
                  <TableCell key={column.value} align="center" sx={{ backgroundColor: chiHeatColor(value, mode), fontWeight: important ? 700 : 400 }}>
                    <Typography>{formatNumber(value)}</Typography>
                    <Typography color="text.secondary" variant="caption">
                      наблюд.: {formatNumber(column.count)}; ожид.: {formatNumber(expected[rowIndex]?.[columnIndex])}
                    </Typography>
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

export function ChiSquareResidualHeatmap({ result }) {
  return (
    <ChiSquareHeatmap
      result={result}
      matrix={result?.chi_square?.standardized_residuals}
      title="Тепловая карта стандартизированных остатков"
      mode="residual"
      helperText="Ячейки с |остатком| ≥ 2 выделены сильнее: они заметно отличаются от ожидаемых частот."
    />
  );
}

export function ChiSquareContributionHeatmap({ result }) {
  return (
    <ChiSquareHeatmap
      result={result}
      matrix={result?.chi_square?.cell_contributions}
      title="Тепловая карта вкладов в χ²"
      mode="contribution"
      helperText="Чем больше значение, тем сильнее ячейка влияет на итоговое значение χ²."
    />
  );
}

export function CrosstabStackedBar({ crosstab }) {
  const rows = crosstab?.rows || [];
  if (!rows.length) return chartEmpty();
  const columnValues = rows[0]?.columns?.map((column) => String(column.label || column.value)) || [];
  const rawData = rows.map((row) => ({
    rowLabel: row.label || row.value,
    shortLabel: truncateLabel(row.label || row.value),
    ...Object.fromEntries((row.columns || []).map((column) => [String(column.label || column.value), Number(column.count) || 0])),
  }));
  const { data, note } = topItems(rawData);

  return (
    <ChartBox minWidth={Math.max(640, data.length * 80)} note={note}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
          <YAxis allowDecimals={false} />
          <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.rowLabel || ""} />
          <Legend />
          {columnValues.map((value, index) => (
            <Bar key={value} dataKey={value} stackId="crosstab" fill={COLORS[index % COLORS.length]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function RegressionCoefficientChart({ result }) {
  const coefficients = (result?.coefficients || [])
    .filter((coefficient) => coefficient.name !== "intercept")
    .map((coefficient) => ({
      label: getVariableLabel(result, coefficient.name),
      shortLabel: truncateLabel(getVariableLabel(result, coefficient.name)),
      value: Number(coefficient.value),
    }))
    .filter((item) => !Number.isNaN(item.value));
  if (!coefficients.length) return chartEmpty("Нет коэффициентов для графика.");
  const { data, note } = topItems(coefficients);

  return (
    <ChartBox minWidth={Math.max(640, data.length * 90)} note={note}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
          <YAxis />
          <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ""} />
          <Bar dataKey="value" name="Коэффициент" fill="#2f80ed" />
        </BarChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function CoefficientConfidenceIntervalChart({ result }) {
  const coefficients = (result?.coefficients || []).filter((item) => item.name !== "intercept" && item.confidence_interval_95);
  if (!coefficients.length) return chartEmpty("Доверительные интервалы коэффициентов недоступны.");
  return (
    <Box sx={{ overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Доверительные интервалы коэффициентов</Typography>
      <Table size="small">
        <TableHead><TableRow><TableCell>Переменная</TableCell><TableCell align="right">Коэффициент</TableCell><TableCell align="right">Нижняя граница</TableCell><TableCell align="right">Верхняя граница</TableCell></TableRow></TableHead>
        <TableBody>{coefficients.map((item) => <TableRow key={item.name}><TableCell>{getVariableLabel(result, item.name)}</TableCell><TableCell align="right">{formatNumber(item.value)}</TableCell><TableCell align="right">{formatNumber(item.confidence_interval_95.low)}</TableCell><TableCell align="right">{formatNumber(item.confidence_interval_95.high)}</TableCell></TableRow>)}</TableBody>
      </Table>
    </Box>
  );
}

export function ObservedVsPredictedChart({ result }) {
  const data = result?.diagnostics?.observed_vs_predicted || [];
  if (!data.length) return chartEmpty("Диагностические точки наблюдаемых и предсказанных значений недоступны.");
  return <ChartBox><ResponsiveContainer><ScatterChart><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" dataKey="observed" name="Наблюдаемое" /><YAxis type="number" dataKey="predicted" name="Предсказанное" /><Tooltip /><Scatter data={data} fill="#2f80ed" /></ScatterChart></ResponsiveContainer></ChartBox>;
}

export function ResidualPlot({ result }) {
  const data = result?.diagnostics?.observed_vs_predicted || [];
  if (!data.length) return chartEmpty("Данные остатков недоступны.");
  return <ChartBox><ResponsiveContainer><ScatterChart><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" dataKey="predicted" name="Предсказанное" /><YAxis type="number" dataKey="residual" name="Остаток" /><Tooltip /><ReferenceLine y={0} stroke="#666" /><Scatter data={data} fill="#eb5757" /></ScatterChart></ResponsiveContainer></ChartBox>;
}

export function ResidualHistogram({ result }) {
  const values = (result?.diagnostics?.residuals || []).map(Number).filter((value) => !Number.isNaN(value));
  if (!values.length) return chartEmpty("Остатки недоступны для гистограммы.");
  const min = Math.min(...values); const max = Math.max(...values); const width = (max - min) / 10 || 1;
  const data = Array.from({ length: 10 }, (_, index) => ({ interval: `${(min + index * width).toFixed(2)}…${(min + (index + 1) * width).toFixed(2)}`, count: 0 }));
  values.forEach((value) => { data[Math.min(9, Math.floor((value - min) / width))].count += 1; });
  return <ChartBox><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="interval" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name="Количество" fill="#56ccf2" /></BarChart></ResponsiveContainer></ChartBox>;
}

export function LogisticOddsRatioChart({ result }) {
  const coefficients = (result?.coefficients || [])
    .filter((coefficient) => coefficient.name !== "intercept")
    .map((coefficient) => ({
      label: getVariableLabel(result, coefficient.name),
      shortLabel: truncateLabel(getVariableLabel(result, coefficient.name)),
      oddsRatio: Number(coefficient.odds_ratio),
    }))
    .filter((item) => !Number.isNaN(item.oddsRatio));
  if (!coefficients.length) return chartEmpty("Нет odds ratio для графика.");
  const { data, note } = topItems(coefficients);

  return (
    <Stack spacing={1}>
      <ChartBox minWidth={Math.max(640, data.length * 90)} note={note}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
            <YAxis />
            <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ""} />
            <ReferenceLine y={1} stroke="#666" strokeDasharray="4 4" />
            <Bar dataKey="oddsRatio" name="Odds ratio" fill="#27ae60" />
          </BarChart>
        </ResponsiveContainer>
      </ChartBox>
      <Typography color="text.secondary" variant="body2">
        Odds ratio &gt; 1 увеличивает шансы события, &lt; 1 уменьшает.
      </Typography>
    </Stack>
  );
}

export function OddsRatioForestPlot({ result }) {
  const coefficients = (result?.coefficients || []).filter((item) => item.name !== "intercept");
  if (!coefficients.length) return chartEmpty("Odds ratio недоступны.");
  return (
    <Box sx={{ overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Odds ratio по факторам</Typography>
      <LogisticOddsRatioChart result={result} />
      <Table size="small"><TableHead><TableRow><TableCell>Фактор</TableCell><TableCell align="right">Odds ratio</TableCell><TableCell align="right">Нижняя граница 95% CI</TableCell><TableCell align="right">Верхняя граница 95% CI</TableCell></TableRow></TableHead><TableBody>{coefficients.map((item) => <TableRow key={item.name}><TableCell>{getVariableLabel(result, item.name)}</TableCell><TableCell align="right">{formatNumber(item.odds_ratio)}</TableCell><TableCell align="right">{formatNumber(item.odds_ratio_confidence_interval_95?.low)}</TableCell><TableCell align="right">{formatNumber(item.odds_ratio_confidence_interval_95?.high)}</TableCell></TableRow>)}</TableBody></Table>
    </Box>
  );
}

export function ConfusionMatrixHeatmap({ result }) {
  const matrix = result?.confusion_matrix;
  if (!matrix) return chartEmpty("Матрица ошибок недоступна.");
  return <Table size="small"><TableHead><TableRow><TableCell /><TableCell align="right">Прогноз: 0</TableCell><TableCell align="right">Прогноз: 1</TableCell></TableRow></TableHead><TableBody><TableRow><TableCell>Факт: 0</TableCell><TableCell align="right" sx={{ backgroundColor: heatColor(matrix.tn, "absolute") }}>{formatNumber(matrix.tn)}</TableCell><TableCell align="right">{formatNumber(matrix.fp)}</TableCell></TableRow><TableRow><TableCell>Факт: 1</TableCell><TableCell align="right">{formatNumber(matrix.fn)}</TableCell><TableCell align="right" sx={{ backgroundColor: heatColor(matrix.tp, "absolute") }}>{formatNumber(matrix.tp)}</TableCell></TableRow></TableBody></Table>;
}

export function RocCurveChart({ result }) {
  const data = result?.roc_curve || [];
  if (!data.length) return chartEmpty("ROC-кривая недоступна.");
  return <ChartBox><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="fpr" type="number" domain={[0, 1]} /><YAxis dataKey="tpr" type="number" domain={[0, 1]} /><Tooltip /><Line dataKey="tpr" name="ROC" stroke="#2f80ed" dot={false} /><ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#666" strokeDasharray="4 4" /></LineChart></ResponsiveContainer></ChartBox>;
}

export function CalibrationPlot({ result }) {
  const data = result?.diagnostics?.calibration?.bins || [];
  if (!data.length) return chartEmpty("Данные калибровки недоступны.");
  return <ChartBox><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="mean_predicted_probability" type="number" domain={[0, 1]} /><YAxis dataKey="observed_event_rate" type="number" domain={[0, 1]} /><Tooltip /><Line dataKey="observed_event_rate" name="Наблюдаемая частота" stroke="#27ae60" /><ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#666" strokeDasharray="4 4" /></LineChart></ResponsiveContainer></ChartBox>;
}

export function ThresholdMetricsChart({ result }) {
  const data = result?.threshold_analysis || [];
  if (!data.length) return chartEmpty("Анализ порогов недоступен.");
  return <ChartBox><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="threshold" /><YAxis domain={[0, 1]} /><Tooltip /><Legend /><Line dataKey="accuracy" stroke="#2f80ed" /><Line dataKey="precision" stroke="#27ae60" /><Line dataKey="recall" stroke="#eb5757" /><Line dataKey="f1" stroke="#9b51e0" /></LineChart></ResponsiveContainer></ChartBox>;
}

export function LogisticProbabilityHistogram({ result }) {
  const probabilities = (result?.predictions || [])
    .map((prediction) => Number(prediction.probability))
    .filter((value) => !Number.isNaN(value));
  if (!probabilities.length) return chartEmpty("Нет predictions[].probability для гистограммы.");
  const buckets = Array.from({ length: 10 }, (_, index) => ({
    interval: `${(index / 10).toFixed(1)}–${((index + 1) / 10).toFixed(1)}`,
    count: 0,
  }));
  probabilities.forEach((value) => {
    const bucketIndex = Math.min(9, Math.max(0, Math.floor(value * 10)));
    buckets[bucketIndex].count += 1;
  });

  return (
    <ChartBox minWidth={640}>
      <ResponsiveContainer>
        <BarChart data={buckets} margin={{ top: 12, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="interval" />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="count" name="Количество" fill="#2f80ed" />
        </BarChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function FactorScreeChart({ result }) {
  const parallelByComponent = new Map((result?.parallel_analysis?.components || []).map((item) => [item.component, item.random_percentile_eigenvalue]));
  const scree = (result?.scree || []).map((item) => ({
    component: item.component,
    eigenvalue: Number(item.eigenvalue),
    explainedPercent: toPercent(item.explained_variance),
    randomPercentile: parallelByComponent.get(item.component),
  }));
  const fallback = (result?.eigenvalues || []).map((value, index) => ({
    component: `Component ${index + 1}`,
    eigenvalue: Number(value),
  }));
  const data = (scree.length ? scree : fallback).filter((item) => !Number.isNaN(item.eigenvalue));
  if (!data.length) return chartEmpty("Нет scree/eigenvalues для графика.");

  return (
    <ChartBox minWidth={Math.max(640, data.length * 80)}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 32 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="component" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
          <ReferenceLine yAxisId="left" y={1} stroke="#666" strokeDasharray="4 4" />
          <Bar yAxisId="right" dataKey="explainedPercent" name="Explained variance, %" fill="#56ccf2" />
          <Line yAxisId="left" type="monotone" dataKey="eigenvalue" name="Eigenvalue" stroke="#eb5757" strokeWidth={2} />
          <Line yAxisId="left" type="monotone" dataKey="randomPercentile" name="Случайный порог" stroke="#9b51e0" strokeDasharray="4 4" />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function FactorLoadingsHeatmap({ result }) {
  const loadings = result?.loadings || [];
  const explainedFactors = result?.explained_variance?.map((item) => item.factor) || [];
  const loadingFactors = loadings[0]?.factors?.map((factor) => factor.factor) || [];
  const factors = explainedFactors.length ? explainedFactors : loadingFactors;
  if (!loadings.length || !factors.length) return chartEmpty("Нет loadings для тепловой карты.");

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Тепловая карта факторных нагрузок</Typography>
      {!!result?.cross_loading_variables?.length && <Alert severity="warning" sx={{ mb: 1 }}>Есть переменные с существенными нагрузками сразу на несколько факторов.</Alert>}
      <Table size="small" sx={{ minWidth: Math.max(640, factors.length * 110) }}>
        <TableHead>
          <TableRow>
            <TableCell>Variable</TableCell>
            <TableCell align="right">Communality</TableCell>
            {factors.map((factor) => <TableCell key={factor} align="right">{factor}</TableCell>)}
          </TableRow>
        </TableHead>
        <TableBody>
          {loadings.map((item) => {
            const factorsByName = new Map((item.factors || []).map((factor) => [factor.factor, factor.loading]));
            return (
              <TableRow key={item.variable}>
                <TableCell>{item.label || item.variable}</TableCell>
                <TableCell align="right">{formatNumber(item.communality)}</TableCell>
                {factors.map((factor) => {
                  const value = factorsByName.get(factor);
                  return (
                    <TableCell key={factor} align="right" sx={{ backgroundColor: heatColor(value, "absolute"), fontWeight: Math.abs(Number(value)) >= 0.4 ? 700 : 400 }}>
                      {formatNumber(value)}
                    </TableCell>
                  );
                })}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Box>
  );
}

export function ParallelAnalysisChart({ result }) {
  const data = (result?.parallel_analysis?.components || []).map((item) => ({
    component: item.component,
    real: Number(item.real_eigenvalue),
    random: Number(item.random_percentile_eigenvalue),
  })).filter((item) => !Number.isNaN(item.real) && !Number.isNaN(item.random));
  if (!data.length) return chartEmpty("Parallel analysis недоступен для этого результата.");
  return <ChartBox><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="component" /><YAxis /><Tooltip /><Legend /><Line dataKey="real" name="Реальные eigenvalues" stroke="#2f80ed" strokeWidth={2} /><Line dataKey="random" name="Случайный порог" stroke="#eb5757" strokeDasharray="4 4" /></LineChart></ResponsiveContainer></ChartBox>;
}

export function ExplainedVarianceChart({ result }) {
  const data = (result?.explained_variance || []).map((item) => ({ factor: item.factor, variance: toPercent(item.explained_variance ?? item.value), cumulative: toPercent(item.cumulative_explained_variance) }));
  if (!data.length) return chartEmpty("Нет данных об объясненной дисперсии.");
  return <ChartBox><ResponsiveContainer><ComposedChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="factor" /><YAxis /><Tooltip /><Legend /><Bar dataKey="variance" name="Дисперсия, %" fill="#2f80ed" /><Line dataKey="cumulative" name="Накопленная доля, %" stroke="#eb5757" /></ComposedChart></ResponsiveContainer></ChartBox>;
}

export function CommunalitiesChart({ result }) {
  const data = (result?.communalities || []).map((item) => ({ label: truncateLabel(item.label || item.variable, 20), communality: Number(item.communality) })).filter((item) => !Number.isNaN(item.communality));
  if (!data.length) return chartEmpty("Communalities недоступны для этого результата.");
  return <ChartBox minWidth={Math.max(640, data.length * 80)}><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" tick={axisTick} interval={0} /><YAxis domain={[0, 1]} /><Tooltip /><ReferenceLine y={0.3} stroke="#eb5757" strokeDasharray="4 4" /><Bar dataKey="communality" name="Communality" fill="#27ae60" /></BarChart></ResponsiveContainer></ChartBox>;
}

export function FactorScoreScatterPlot({ result }) {
  const data = (result?.factor_scores || []).map((item) => ({ x: Number(item["Фактор 1"] ?? item.scores?.[0]?.value), y: Number(item["Фактор 2"] ?? item.scores?.[1]?.value) })).filter((item) => !Number.isNaN(item.x) && !Number.isNaN(item.y));
  if (!data.length) return chartEmpty("Факторные значения не были сохранены. Включите расчет factor scores.");
  return <ChartBox><ResponsiveContainer><ScatterChart><CartesianGrid /><XAxis type="number" dataKey="x" name="Фактор 1" /><YAxis type="number" dataKey="y" name="Фактор 2" /><Tooltip cursor={{ strokeDasharray: "3 3" }} /><Scatter data={data} fill="#2f80ed" /></ScatterChart></ResponsiveContainer></ChartBox>;
}

export function PcaBiplotChart({ result }) {
  if (!result?.biplot?.available) return chartEmpty("Для biplot требуется не менее двух факторов и сохраненные factor scores.");
  return <Stack spacing={1}><FactorScoreScatterPlot result={result} /><Typography variant="subtitle2">Векторы переменных</Typography>{(result.biplot.vectors || []).map((item) => <Typography variant="body2" key={item.variable}>{item.label || item.variable}: ({formatNumber(item.x)}; {formatNumber(item.y)})</Typography>)}</Stack>;
}

export function ClusterSizeChart({ result }) {
  const clusters = (result?.clusters || result?.cluster_sizes || []).map((cluster) => ({
    cluster: cluster.label || `Кластер ${cluster.cluster}`,
    size: Number(cluster.size ?? cluster.count),
    percent: cluster.percent,
  })).filter((item) => !Number.isNaN(item.size));
  if (!clusters.length) return chartEmpty();

  return (
    <ChartBox minWidth={640}>
      <ResponsiveContainer>
        <BarChart data={clusters} margin={{ top: 12, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="cluster" />
          <YAxis allowDecimals={false} />
          <Tooltip formatter={(value, name, item) => [value, `${name} (${formatNumber(item.payload.percent)}%)`]} />
          <Bar dataKey="size" name="Размер" fill="#2f80ed" />
        </BarChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function ClusterTopFeaturesChart({ result }) {
  const profiles = result?.cluster_profiles || [];
  if (!profiles.length) return chartEmpty("Нет профилей кластеров для графика.");

  return (
    <Stack spacing={2}>
      {profiles.map((profile) => {
        const features = (profile.top_distinguishing_features || []).slice(0, 5).map((feature) => ({
          label: feature.label || feature.variable || feature.code,
          shortLabel: truncateLabel(feature.label || feature.variable || feature.code, 22),
          difference: Number(feature.difference ?? feature.difference_pp ?? feature.z_difference ?? feature.cluster_value),
        })).filter((item) => !Number.isNaN(item.difference));
        if (!features.length) return null;
        return (
          <Box key={profile.cluster}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Ключевые отличия кластера {profile.cluster}
            </Typography>
            <ChartBox height={SMALL_CHART_HEIGHT} minWidth={Math.max(560, features.length * 90)}>
              <ResponsiveContainer>
                <BarChart data={features} margin={{ top: 8, right: 24, left: 8, bottom: 52 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
                  <YAxis />
                  <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ""} />
                  <Bar dataKey="difference" name="Отличие" fill="#9b51e0" />
                </BarChart>
              </ResponsiveContainer>
            </ChartBox>
          </Box>
        );
      })}
    </Stack>
  );
}

export function ClusterProfileHeatmap({ result }) {
  const rows = result?.profile_heatmap?.rows || (result?.cluster_profiles || []).map((profile) => ({ cluster_label: profile.label || `Кластер ${profile.cluster}`, values: profile.profile_values || [] }));
  const variables = rows[0]?.values || [];
  if (!rows.length || !variables.length) return chartEmpty("Профиль кластеров недоступен для этого результата.");
  return <Box sx={{ overflowX: "auto" }}><Typography variant="subtitle1">Тепловая карта профилей кластеров</Typography><Table size="small"><TableHead><TableRow><TableCell>Кластер</TableCell>{variables.map((item) => <TableCell key={item.code} align="right">{item.label || item.code}</TableCell>)}</TableRow></TableHead><TableBody>{rows.map((row) => <TableRow key={row.cluster_label || row.cluster}><TableCell>{row.cluster_label || `Кластер ${row.cluster}`}</TableCell>{(row.values || []).map((item) => { const value = item.standardized_value ?? item.standardized_difference ?? item.value; return <TableCell key={item.code} align="right" sx={{ backgroundColor: heatColor(value, "absolute") }}>{formatNumber(value)}</TableCell>; })}</TableRow>)}</TableBody></Table></Box>;
}

export function ClusterPcaScatterPlot({ result }) {
  const points = result?.dimension_reduction?.points || [];
  if (!result?.dimension_reduction?.available || !points.length) return chartEmpty("Для двумерной визуализации кластеров недостаточно данных.");
  const clusters = [...new Set(points.map((item) => item.cluster))];
  return <ChartBox><ResponsiveContainer><ScatterChart><CartesianGrid /><XAxis type="number" dataKey="x" name="PC1" /><YAxis type="number" dataKey="y" name="PC2" /><Tooltip cursor={{ strokeDasharray: "3 3" }} /><Legend />{clusters.map((cluster, index) => <Scatter key={cluster} name={`Кластер ${cluster}`} data={points.filter((item) => item.cluster === cluster)} fill={COLORS[index % COLORS.length]} />)}</ScatterChart></ResponsiveContainer></ChartBox>;
}

export function ClusterRadarChart({ result }) {
  const profiles = result?.radar_profiles || [];
  if (!profiles.length) return chartEmpty("Radar profile недоступен для этого результата.");
  return <Box sx={{ overflowX: "auto" }}><Typography variant="subtitle1">Radar-профили кластеров</Typography><Table size="small"><TableHead><TableRow><TableCell>Кластер</TableCell><TableCell>Признак</TableCell><TableCell align="right">Стандартизированное значение</TableCell></TableRow></TableHead><TableBody>{profiles.flatMap((profile) => (profile.values || []).map((item) => <TableRow key={`${profile.cluster}-${item.code}`}><TableCell>{profile.cluster_label || `Кластер ${profile.cluster}`}</TableCell><TableCell>{item.axis || item.code}</TableCell><TableCell align="right">{formatNumber(item.value)}</TableCell></TableRow>))}</TableBody></Table></Box>;
}

export function SilhouettePlot({ result }) {
  const data = result?.silhouette?.cluster_summary || [];
  if (!data.length) return chartEmpty("Silhouette plot недоступен для этого результата.");
  return <ChartBox><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" /><YAxis domain={[-1, 1]} /><Tooltip /><Legend /><ReferenceLine y={0} stroke="#666" /><Bar dataKey="mean_silhouette" name="Средний silhouette" fill="#27ae60" /><Bar dataKey="min_silhouette" name="Минимальный silhouette" fill="#eb5757" /></BarChart></ResponsiveContainer></ChartBox>;
}

export function ElbowPlot({ result }) {
  const data = result?.elbow?.points || [];
  if (!data.length) return chartEmpty("Elbow plot недоступен для этого результата.");
  return <Stack spacing={1}><ChartBox><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="k" /><YAxis /><Tooltip /><ReferenceLine x={result.elbow.suggested_k} stroke="#eb5757" strokeDasharray="4 4" /><Line dataKey="inertia" name="Inertia" stroke="#2f80ed" strokeWidth={2} /></LineChart></ResponsiveContainer></ChartBox><Typography color="text.secondary" variant="body2">{result.elbow.interpretation}</Typography></Stack>;
}

export function ClusterDistanceChart({ result }) {
  const data = result?.cluster_distances?.summary || [];
  if (!data.length) return chartEmpty("Расстояния до центроидов недоступны для этого результата.");
  return <ChartBox><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" /><YAxis /><Tooltip /><Legend /><Bar dataKey="mean_distance_to_centroid" name="Среднее расстояние" fill="#2f80ed" /><Bar dataKey="max_distance_to_centroid" name="Максимальное расстояние" fill="#f2994a" /></BarChart></ResponsiveContainer></ChartBox>;
}

export function GroupComparisonMeanChart({ result }) {
  const groups = (result?.groups || []).map((group) => ({
    label: group.label || group.group,
    shortLabel: truncateLabel(group.label || group.group),
    value: Number(group.mean ?? group.median),
    mean: group.mean,
    median: group.median,
    std: group.std,
    n: group.n,
  })).filter((item) => !Number.isNaN(item.value));
  if (!groups.length) return chartEmpty("Нет средних/медиан для графика.");
  const { data, note } = topItems(groups);

  return (
    <ChartBox minWidth={Math.max(640, data.length * 90)} note={note}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
          <YAxis />
          <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ""} />
          <Bar dataKey="value" name="Mean/median" fill="#27ae60" />
        </BarChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function GroupMeanCiChart({ result }) {
  const groups = result?.groups || [];
  const hasIntervals = groups.some((group) => group.confidence_interval_95);
  return (
    <Stack spacing={1}>
      <Typography variant="subtitle1">Средние значения по группам</Typography>
      <GroupComparisonMeanChart result={result} />
      <Typography color="text.secondary" variant="body2">
        {hasIntervals
          ? "Доверительные интервалы доступны в таблице групп."
          : "Доверительные интервалы недоступны для этого результата."}
      </Typography>
      {hasIntervals && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Группа</TableCell>
              <TableCell align="right">Среднее</TableCell>
              <TableCell align="right">Нижняя граница 95% CI</TableCell>
              <TableCell align="right">Верхняя граница 95% CI</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groups.map((group) => (
              <TableRow key={`mean-ci-${String(group.group ?? group.group_value)}`}>
                <TableCell>{group.label || group.group_label || group.group}</TableCell>
                <TableCell align="right">{formatNumber(group.mean)}</TableCell>
                <TableCell align="right">{formatNumber(group.confidence_interval_95?.low)}</TableCell>
                <TableCell align="right">{formatNumber(group.confidence_interval_95?.high)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Stack>
  );
}

export function GroupBoxplotApproxChart({ result }) {
  const groups = result?.groups || [];
  if (!groups.length) return null;
  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Boxplot по группам</Typography>
      <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
        Boxplot показывает медиану, квартильный размах и возможные выбросы. В интерфейсе отображается табличное представление boxplot-показателей.
      </Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Группа</TableCell>
            <TableCell align="right">Мин</TableCell>
            <TableCell align="right">Q1</TableCell>
            <TableCell align="right">Медиана</TableCell>
            <TableCell align="right">Q3</TableCell>
            <TableCell align="right">Макс</TableCell>
            <TableCell align="right">Выбросы</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {groups.map((group) => (
            <TableRow key={String(group.group ?? group.group_value)}>
              <TableCell>{group.label || group.group_label || group.group}</TableCell>
              <TableCell align="right">{formatNumber(group.min)}</TableCell>
              <TableCell align="right">{formatNumber(group.q1)}</TableCell>
              <TableCell align="right">{formatNumber(group.median)}</TableCell>
              <TableCell align="right">{formatNumber(group.q3)}</TableCell>
              <TableCell align="right">{formatNumber(group.max)}</TableCell>
              <TableCell align="right">{formatNumber(group.outliers_count)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

export function ReliabilityItemChart({ result }) {
  const items = (result?.item_statistics || []).map((item) => ({
    label: item.label || item.code,
    shortLabel: truncateLabel(item.label || item.code),
    itemTotalCorrelation: Number(item.item_total_correlation),
    alphaIfDeleted: Number(item.alpha_if_deleted),
  }));
  const { data, note } = topItems(items.filter((item) => !Number.isNaN(item.itemTotalCorrelation)));
  if (!data.length) return chartEmpty("Нет item statistics для графика.");

  return (
    <ChartBox minWidth={Math.max(640, data.length * 90)} note={note}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
          <YAxis />
          <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ""} />
          <Legend />
          <Bar dataKey="itemTotalCorrelation" name="Item-total correlation" fill="#2f80ed" />
          <Line type="monotone" dataKey="alphaIfDeleted" name="Alpha if deleted" stroke="#eb5757" strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function ItemTotalCorrelationChart({ result }) {
  const items = result?.item_total_correlations || result?.reliability?.item_total_correlations || result?.item_statistics || [];
  const data = items.map((item) => ({ label: truncateLabel(item.label || item.code, 20), value: Number(item.item_total_correlation) })).filter((item) => !Number.isNaN(item.value));
  if (!data.length) return chartEmpty("Item-total correlation недоступна.");
  return <ChartBox minWidth={Math.max(640, data.length * 90)}><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" tick={axisTick} interval={0} /><YAxis /><Tooltip /><ReferenceLine y={0.3} stroke="#eb5757" strokeDasharray="4 4" /><Bar dataKey="value" name="Item-total correlation" fill="#2f80ed" /></BarChart></ResponsiveContainer></ChartBox>;
}

export function AlphaIfDeletedTable({ result }) {
  const items = result?.alpha_if_item_deleted || result?.reliability?.alpha_if_item_deleted || [];
  if (!items.length) return chartEmpty("Alpha if item deleted недоступна.");
  return <Box sx={{ overflowX: "auto" }}><Typography variant="subtitle1">Alpha if item deleted</Typography><Table size="small"><TableHead><TableRow><TableCell>Пункт</TableCell><TableCell align="right">Alpha</TableCell><TableCell align="right">Delta</TableCell><TableCell>Повышает alpha</TableCell><TableCell>Интерпретация</TableCell></TableRow></TableHead><TableBody>{items.map((item) => <TableRow key={item.code} sx={{ backgroundColor: item.improves_alpha ? "rgba(242, 201, 76, 0.2)" : undefined }}><TableCell>{item.label || item.code}</TableCell><TableCell align="right">{formatNumber(item.alpha_if_deleted)}</TableCell><TableCell align="right">{formatNumber(item.delta_alpha)}</TableCell><TableCell>{item.improves_alpha ? "да" : "нет"}</TableCell><TableCell>{item.interpretation || "—"}</TableCell></TableRow>)}</TableBody></Table></Box>;
}

export function InterItemCorrelationHeatmap({ result }) {
  const correlations = result?.inter_item_correlations || result?.reliability?.inter_item_correlations || {};
  const variables = correlations.variables || result?.variables || [];
  const matrix = correlations.matrix || result?.inter_item_correlation_matrix || [];
  if (!variables.length || !matrix.length) return chartEmpty("Матрица межпунктовых корреляций недоступна.");
  return <Box sx={{ overflowX: "auto" }}><Typography variant="subtitle1">Межпунктовые корреляции</Typography><Table size="small"><TableHead><TableRow><TableCell>Пункт</TableCell>{variables.map((item) => <TableCell key={item.code} align="right">{truncateLabel(item.label || item.code, 18)}</TableCell>)}</TableRow></TableHead><TableBody>{variables.map((variable, rowIndex) => <TableRow key={variable.code}><TableCell>{variable.label || variable.code}</TableCell>{variables.map((column, columnIndex) => <TableCell key={column.code} align="right" sx={{ backgroundColor: heatColor(matrix[rowIndex]?.[columnIndex]) }}>{formatNumber(matrix[rowIndex]?.[columnIndex])}</TableCell>)}</TableRow>)}</TableBody></Table></Box>;
}

export function TimeDistributionChart({ data, title }) {
  const rows = (data || []).map((item) => ({
    label: item.label,
    count: Number(item.count),
    percent: item.percent,
  })).filter((item) => !Number.isNaN(item.count));
  if (!rows.length) return chartEmpty();

  return (
    <Box>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>{title}</Typography>
      <ChartBox minWidth={640}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 12, right: 24, left: 8, bottom: 32 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" name="Количество" fill="#2f80ed" />
          </BarChart>
        </ResponsiveContainer>
      </ChartBox>
    </Box>
  );
}

export function TimeScreenoutReasonsChart({ result }) {
  const { data, note } = topItems((result?.screenout?.reasons || result?.screenout_reasons || []).map((reason) => ({
    label: reason.reason,
    shortLabel: truncateLabel(reason.reason),
    count: Number(reason.count),
  })).filter((item) => !Number.isNaN(item.count)));
  if (!data.length) return chartEmpty("Нет причин отсева для графика.");

  return (
    <ChartBox minWidth={Math.max(640, data.length * 90)} note={note}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
          <YAxis allowDecimals={false} />
          <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ""} />
          <Bar dataKey="count" name="Количество" fill="#eb5757" />
        </BarChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function TimeFunnelChart({ result }) {
  const data = result?.page_funnel?.steps || [];
  if (!data.length) return chartEmpty("Воронка прохождения недоступна.");
  return <ChartBox><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" tick={axisTick} interval={0} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name="Респонденты" fill="#2f80ed" /></BarChart></ResponsiveContainer></ChartBox>;
}

export function RetentionCurveChart({ result }) {
  const data = result?.retention_curve?.points || [];
  if (!data.length) return chartEmpty("Retention curve недоступна.");
  return <ChartBox><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" tick={axisTick} interval={0} /><YAxis domain={[0, 100]} /><Tooltip /><Line dataKey="retention_rate" name="Retention, %" stroke="#27ae60" strokeWidth={2} /></LineChart></ResponsiveContainer></ChartBox>;
}

export function CompletionTimeBoxplotApprox({ result }) {
  const summary = result?.duration_summary || {};
  if (!summary.count) return chartEmpty("Boxplot-показатели времени недоступны.");
  return <Typography color="text.secondary" variant="body2">Boxplot-показатели: min {formatNumber(summary.min_seconds)}, P25 {formatNumber(summary.p25_seconds)}, медиана {formatNumber(summary.median_seconds)}, P75 {formatNumber(summary.p75_seconds)}, max {formatNumber(summary.max_seconds)}, IQR {formatNumber(summary.iqr_seconds)}.</Typography>;
}

export function DropoutByPageChart({ result }) {
  const data = result?.dropout?.by_page || [];
  if (!data.length) return chartEmpty("Dropout по страницам недоступен.");
  return <ChartBox><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="page_title" /><YAxis /><Tooltip /><Bar dataKey="dropout_rate" name="Dropout, %" fill="#eb5757" /></BarChart></ResponsiveContainer></ChartBox>;
}

export function GroupTimeBoxplotApprox({ result }) {
  const rows = result?.group_comparison?.groups || [];
  if (!rows.length) return chartEmpty("Сравнение времени по группам недоступно.");
  return <Box sx={{ overflowX: "auto" }}><Typography variant="subtitle1">Время по группам</Typography><Table size="small"><TableHead><TableRow><TableCell>Группа</TableCell><TableCell align="right">n</TableCell><TableCell align="right">Медиана</TableCell><TableCell align="right">Среднее</TableCell><TableCell align="right">P25</TableCell><TableCell align="right">P75</TableCell></TableRow></TableHead><TableBody>{rows.map((item) => <TableRow key={String(item.group_value)}><TableCell>{item.group_label}</TableCell><TableCell align="right">{formatNumber(item.n)}</TableCell><TableCell align="right">{formatNumber(item.median_seconds)}</TableCell><TableCell align="right">{formatNumber(item.average_seconds)}</TableCell><TableCell align="right">{formatNumber(item.p25_seconds)}</TableCell><TableCell align="right">{formatNumber(item.p75_seconds)}</TableCell></TableRow>)}</TableBody></Table></Box>;
}

export function ResponseQualityFlagsTable({ result }) {
  const rows = (result?.response_flags || []).slice(0, 50);
  if (!rows.length) return chartEmpty("Флаги качества ответов не обнаружены.");
  return <Box sx={{ overflowX: "auto" }}><Typography variant="subtitle1">Прохождения, требующие проверки</Typography><Table size="small"><TableHead><TableRow><TableCell>ID</TableCell><TableCell align="right">Длительность</TableCell><TableCell>Флаги</TableCell><TableCell>Причина</TableCell></TableRow></TableHead><TableBody>{rows.map((item) => <TableRow key={item.response_id}><TableCell>{item.response_id}</TableCell><TableCell align="right">{formatNumber(item.duration_seconds)}</TableCell><TableCell>{(item.flags || []).join(", ")}</TableCell><TableCell>{item.reason}</TableCell></TableRow>)}</TableBody></Table></Box>;
}

export function TimeFlowTable({ result }) {
  const links = result?.flow?.links || [];
  if (!links.length) return chartEmpty("Поток прохождения недоступен.");
  return <Box sx={{ overflowX: "auto" }}><Typography variant="subtitle1">Агрегированный поток прохождения</Typography><Table size="small"><TableHead><TableRow><TableCell>Откуда</TableCell><TableCell>Куда</TableCell><TableCell align="right">Респондентов</TableCell></TableRow></TableHead><TableBody>{links.map((item, index) => <TableRow key={`${item.source}-${item.target}-${index}`}><TableCell>{item.source}</TableCell><TableCell>{item.target}</TableCell><TableCell align="right">{formatNumber(item.value)}</TableCell></TableRow>)}</TableBody></Table></Box>;
}

export function MissingAnalysisChart({ result }) {
  const { data, note } = topItems((result?.questions || []).map((question) => ({
    label: question.label || question.question_id,
    shortLabel: truncateLabel(question.label || question.question_id),
    answered: Number(question.answered_count) || 0,
    skipped: Number(question.skipped_count) || 0,
    notShown: Number(question.not_shown_count) || 0,
  })), 15);
  if (!data.length) return chartEmpty();

  return (
    <Stack spacing={1}>
      <ChartBox minWidth={Math.max(760, data.length * 90)} note={note}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
            <YAxis allowDecimals={false} />
            <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ""} />
            <Legend />
            <Bar dataKey="answered" stackId="missing" name="Ответили" fill="#27ae60" />
            <Bar dataKey="skipped" stackId="missing" name="Пропустили" fill="#eb5757" />
            <Bar dataKey="notShown" stackId="missing" name="Не показали" fill="#f2c94c" />
          </BarChart>
        </ResponsiveContainer>
      </ChartBox>
      <Alert severity="info">Не показан из-за ветвления не считается реальным пропуском.</Alert>
    </Stack>
  );
}

export function MissingStackedStatusChart({ result }) {
  const detailed = result?.detailed_missing_analysis;
  const { data, note } = topItems((detailed?.questions || []).map((question) => ({
    label: question.label || question.question_id,
    shortLabel: truncateLabel(question.label || question.question_id),
    answered: Number(question.counts?.answered) || 0,
    skippedAfterShown: Number(question.counts?.skipped_after_shown) || 0,
    notShownByBranching: Number(question.counts?.not_shown_by_branching) || 0,
    notReached: Number(question.counts?.not_reached) || 0,
    screenedOut: Number(question.counts?.screened_out) || 0,
  })), 15);
  if (!data.length) return null;

  return (
    <Stack spacing={1}>
      <Typography variant="subtitle1">Причины отсутствия ответов</Typography>
      <ChartBox minWidth={Math.max(760, data.length * 90)} note={note}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 12, right: 24, left: 8, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="shortLabel" tick={axisTick} interval={0} />
            <YAxis allowDecimals={false} />
            <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ""} />
            <Legend />
            <Bar dataKey="answered" stackId="missing-status" name="Ответили" fill="#27ae60" />
            <Bar dataKey="skippedAfterShown" stackId="missing-status" name="Пропустили после показа" fill="#eb5757" />
            <Bar dataKey="notShownByBranching" stackId="missing-status" name="Не показан из-за ветвления" fill="#f2c94c" />
            <Bar dataKey="notReached" stackId="missing-status" name="Не дошли" fill="#56ccf2" />
            <Bar dataKey="screenedOut" stackId="missing-status" name="Отсев" fill="#9b51e0" />
          </BarChart>
        </ResponsiveContainer>
      </ChartBox>
    </Stack>
  );
}

export function ScaleIndexDistributionChart({ result }) {
  const rows = (result?.distribution || result?.score_distribution || []).map((item) => ({
    label: item.label,
    count: Number(item.count),
    percent: item.percent,
  })).filter((item) => !Number.isNaN(item.count));
  if (!rows.length) return chartEmpty("Нет score_distribution для графика.");

  return (
    <ChartBox minWidth={640}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 12, right: 24, left: 8, bottom: 32 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="count" name="Количество" fill="#2f80ed" />
        </BarChart>
      </ResponsiveContainer>
    </ChartBox>
  );
}

export function ScaleIndexScoreCard({ result }) {
  const normalized = result?.normalized_score_summary || {};
  const raw = result?.score_summary || {};
  return <Box sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 2 }}><Typography variant="subtitle1">Сводка индекса</Typography><Typography>Среднее: {formatNumber(normalized.mean ?? raw.mean)}{normalized.mean !== null && normalized.mean !== undefined ? " из 100" : ""}</Typography><Typography variant="body2" color="text.secondary">Медиана: {formatNumber(normalized.median ?? raw.median)} · n: {formatNumber(result?.n ?? result?.n_scored)} · alpha: {formatNumber(result?.reliability?.cronbach_alpha ?? result?.reliability?.alpha)}</Typography></Box>;
}

export function ScaleIndexGroupsChart({ result }) {
  const data = result?.groups?.items || [];
  if (!data.length) return chartEmpty("Группы уровней индекса недоступны.");
  return <ChartBox><ResponsiveContainer><BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name="Респонденты" fill="#27ae60" /></BarChart></ResponsiveContainer></ChartBox>;
}

export function ScaleIndexBoxplotApprox({ result }) {
  const summary = result?.normalized_score_summary?.n ? result.normalized_score_summary : result?.score_summary || {};
  if (!summary.n) return chartEmpty("Boxplot-показатели индекса недоступны.");
  return <Box><Typography variant="subtitle1">Boxplot-показатели индекса</Typography><Typography color="text.secondary" variant="body2">Табличное представление: min {formatNumber(summary.min)}, Q1 {formatNumber(summary.p25)}, медиана {formatNumber(summary.median)}, Q3 {formatNumber(summary.p75)}, max {formatNumber(summary.max)}.</Typography></Box>;
}

export function ScaleItemsCorrelationHeatmap({ result }) {
  return <InterItemCorrelationHeatmap result={result?.reliability || {}} />;
}

export function CorrespondenceInertiaChart({ result }) {
  const dimensions = (result?.dimensions || []).map((dimension) => ({
    dimension: dimension.dimension,
    explainedPercent: toPercent(dimension.explained_inertia),
  })).filter((item) => item.explainedPercent !== null);
  if (!dimensions.length) return chartEmpty("Нет dimensions для графика инерции.");

  const rowPoints = (result?.row_coordinates || []).map((point) => coordinatesToPoint(point)).filter(hasCoordinates);
  const columnPoints = (result?.column_coordinates || []).map((point) => coordinatesToPoint(point)).filter(hasCoordinates);
  const hasScatter = rowPoints.length + columnPoints.length > 0;

  return (
    <Stack spacing={2}>
      <ChartBox minWidth={640}>
        <ResponsiveContainer>
          <BarChart data={dimensions} margin={{ top: 12, right: 24, left: 8, bottom: 32 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="dimension" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="explainedPercent" name="Explained inertia, %" fill="#2f80ed" />
          </BarChart>
        </ResponsiveContainer>
      </ChartBox>
      {hasScatter && (
        <ChartBox minWidth={640}>
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 12, right: 24, left: 8, bottom: 32 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="x" name="Dim 1" />
              <YAxis type="number" dataKey="y" name="Dim 2" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value) => formatNumber(value)} />
              <Legend />
              <Scatter name="Строки" data={rowPoints} fill="#2f80ed" />
              <Scatter name="Столбцы" data={columnPoints} fill="#eb5757" />
            </ScatterChart>
          </ResponsiveContainer>
        </ChartBox>
      )}
    </Stack>
  );
}

function coordinatesToPoint(point) {
  const values = new Map((point.coordinates || []).map((item) => [item.dimension, Number(item.value)]));
  return {
    label: point.label || point.value,
    x: values.get("Dim 1") ?? values.get("Dimension 1") ?? values.get("1") ?? [...values.values()][0],
    y: values.get("Dim 2") ?? values.get("Dimension 2") ?? values.get("2") ?? [...values.values()][1],
  };
}

function hasCoordinates(point) {
  return !Number.isNaN(Number(point.x)) && !Number.isNaN(Number(point.y));
}
