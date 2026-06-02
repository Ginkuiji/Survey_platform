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
  const scree = (result?.scree || []).map((item) => ({
    component: item.component,
    eigenvalue: Number(item.eigenvalue),
    explainedPercent: toPercent(item.explained_variance),
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
                    <TableCell key={factor} align="right" sx={{ backgroundColor: heatColor(value, "absolute") }}>
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

export function ClusterSizeChart({ result }) {
  const clusters = (result?.clusters || []).map((cluster) => ({
    cluster: `Кластер ${cluster.cluster}`,
    size: Number(cluster.size),
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
  const { data, note } = topItems((result?.screenout_reasons || []).map((reason) => ({
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
  const rows = (result?.score_distribution || []).map((item) => ({
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
