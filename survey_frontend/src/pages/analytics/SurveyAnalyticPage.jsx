import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { deleteSurvey, fetchAdminSurveyById } from "../../api/surveys";
import {
  createAnalyticResult,
  exportAnalyticsCsv,
  exportAnalyticsPdf,
  exportAnalyticsXlsx,
  fetchAnalysisReports,
  fetchAnalyticResultById,
  fetchAnalyticResults,
  fetchSurveyAnalytics,
} from "../../api/analytics";

const CHART_COLORS = ["#2f80ed", "#27ae60", "#f2c94c", "#eb5757", "#9b51e0", "#56ccf2"];
const PIE_CHART_WIDTH = 360;
const BAR_CHART_WIDTH = 560;
const CHART_HEIGHT = 300;
const LEGEND_LABEL_MAX_LENGTH = 24;

function getDefaultSnapshotTitle() {
  return `Срез от ${new Intl.DateTimeFormat("ru-RU").format(new Date())}`;
}

const QUESTION_TYPE_LABELS = {
  single: "Одиночный выбор",
  multi: "Множественный выбор",
  dropdown: "Выпадающий список",
  yesno: "Да/Нет",
  text: "Текст",
  scale: "Шкала",
  number: "Число",
  date: "Дата",
  matrix_single: "Матрица: один выбор",
  matrix_multi: "Матрица: много выборов",
  ranking: "Ранжирование",
};

function formatNumber(value) {
  if (value === null || value === undefined) return "Нет данных";
  return Number.isInteger(value) ? value : Number(value).toFixed(2);
}

function formatSeconds(value) {
  if (value === null || value === undefined) return "Нет данных";
  if (value < 60) return `${formatNumber(value)} сек.`;
  return `${formatNumber(value / 60)} мин.`;
}

function truncateLegendLabel(value) {
  const label = String(value ?? "");
  if (label.length <= LEGEND_LABEL_MAX_LENGTH) return label;
  return `${label.slice(0, LEGEND_LABEL_MAX_LENGTH - 1)}...`;
}

function Metric({ label, value }) {
  return (
    <Box sx={{ minWidth: 150 }}>
      <Typography color="text.secondary" variant="body2">
        {label}
      </Typography>
      <Typography variant="h6">{value}</Typography>
    </Box>
  );
}

function SummaryBlock({ summary }) {
  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Сводка по опросу
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} flexWrap="wrap" useFlexGap>
          <Metric label="Завершили" value={summary.total_completed ?? 0} />
          <Metric label="Начали" value={summary.total_started ?? 0} />
          <Metric label="Завершение" value={`${summary.completion_rate ?? 0}%`} />
          <Metric label="Вопросов" value={summary.questions_count ?? 0} />
          <Metric label="Среднее время" value={formatSeconds(summary.average_completion_time)} />
        </Stack>
      </CardContent>
    </Card>
  );
}

function EnhancedSummaryBlock({ summary }) {
  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Сводка по опросу
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} flexWrap="wrap" useFlexGap>
          <Metric label="Завершили полностью" value={summary.total_completed ?? 0} />
          <Metric label="Отсечены" value={summary.total_screened_out ?? 0} />
          <Metric label="Всего завершили" value={summary.total_finished ?? 0} />
          <Metric label="Начали" value={summary.total_started ?? 0} />
          <Metric label="Полностью прошли %" value={`${summary.completion_rate ?? 0}%`} />
          <Metric label="Отсечены %" value={`${summary.screenout_rate ?? 0}%`} />
          <Metric label="Завершили %" value={`${summary.finish_rate ?? 0}%`} />
          <Metric label="Среднее время завершения" value={formatSeconds(summary.average_completion_time)} />
          <Metric label="Среднее до скрининга" value={formatSeconds(summary.average_screenout_time)} />
          <Metric label="Вопросов" value={summary.questions_count ?? 0} />
        </Stack>
      </CardContent>
    </Card>
  );
}

function ScreeningBlock({ screening }) {
  const reasons = screening?.reasons ?? [];

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Скрининг
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
          <Metric label="Отсечены" value={screening?.total_screened_out ?? 0} />
          <Metric label="Среднее до скрининга" value={formatSeconds(screening?.average_screenout_time)} />
        </Stack>

        {reasons.length ? (
          <Stack spacing={1}>
            {reasons.map(item => (
              <Stack key={item.reason} direction="row" justifyContent="space-between" spacing={2}>
                <Typography>{item.reason}</Typography>
                <Typography color="text.secondary">{item.count}</Typography>
              </Stack>
            ))}
          </Stack>
        ) : (
          <Typography color="text.secondary" variant="body2">
            Screened out ответов пока нет.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

function QuestionBase({ base }) {
  return (
    <Box sx={{ mb: 2 }}>
      <Alert severity="info" sx={{ mb: 2 }}>
        База расчёта: вопрос был показан {base?.shown_count ?? 0} респондентам,
        ответили {base?.answered_count ?? 0}, пропустили {base?.skipped_count ?? 0}.
        Проценты по вариантам можно смотреть от ответивших, от видевших вопрос и от всех завершивших опрос.
      </Alert>
      {(base?.not_shown_count ?? 0) > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Вопрос был показан не всем респондентам из-за логики ветвления; проценты следует интерпретировать с учетом базы «видели вопрос».
        </Alert>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} flexWrap="wrap" useFlexGap>
        <Metric label="Завершили опрос" value={base?.total_completed ?? 0} />
        <Metric label="Видели вопрос" value={base?.shown_count ?? 0} />
        <Metric label="Ответили" value={base?.answered_count ?? 0} />
        <Metric label="Пропустили" value={base?.skipped_count ?? 0} />
      </Stack>
    </Box>
  );
}

function ChoiceAnalytics({ question }) {
  const options = question.result?.options ?? [];
  const useHorizontalBar = options.length > 4;

  if (!options.length) {
    return (
      <Typography color="text.secondary" variant="body2">
        Вариантов ответа пока нет.
      </Typography>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={5} sx={{ minWidth: 0 }}>
        <Box sx={{ width: "100%", overflowX: "auto", display: "flex", justifyContent: "center" }}>
          <PieChart width={PIE_CHART_WIDTH} height={CHART_HEIGHT}>
              <Pie
                data={options}
                dataKey="count"
                nameKey="text"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
                label={false}
                labelLine={false}
                // label={({ percent }) => `${Math.round(percent * 100)}%`}
              >
                {options.map((option, index) => (
                  <Cell key={option.id} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value, name, item) => [
                  `${value} ответов`,
                  item.payload?.text ?? name,
                ]}
              />
              <Legend formatter={truncateLegendLabel} />
          </PieChart>
        </Box>
      </Grid>

      <Grid item xs={12} md={7} sx={{ minWidth: 0 }}>
        {useHorizontalBar && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Для данного вопроса горизонтальная столбчатая диаграмма предпочтительнее круговой диаграммы.
          </Alert>
        )}
        <Box sx={{ mb: 2, width: "100%", overflowX: "auto" }}>
          <BarChart
            width={BAR_CHART_WIDTH}
            height={useHorizontalBar ? Math.max(CHART_HEIGHT, options.length * 42) : CHART_HEIGHT}
            data={options}
            layout={useHorizontalBar ? "vertical" : "horizontal"}
          >
              <CartesianGrid strokeDasharray="3 3" />
              {useHorizontalBar ? <XAxis type="number" /> : <XAxis dataKey="text" />}
              {useHorizontalBar ? <YAxis dataKey="text" type="category" width={150} /> : <YAxis allowDecimals={false} />}
              <Tooltip />
              <Legend />
              <Bar dataKey="count" name="Ответов" fill="#2f80ed" />
          </BarChart>
        </Box>

        <Stack spacing={1.5}>
          {options.map(option => (
            <Box key={option.id}>
              <Stack direction="row" justifyContent="space-between" spacing={2}>
                <Typography>{option.text}</Typography>
                <Typography color="text.secondary">
                  {option.count} · {option.percent_answered}% от ответивших · {option.percent_shown ?? option.percent_answered}% от видевших · {option.percent_total}% от завершивших
                </Typography>
              </Stack>
              <LinearProgress
                variant="determinate"
                value={Math.min(option.percent_answered ?? 0, 100)}
                sx={{ mt: 0.5, height: 8, borderRadius: 1 }}
              />
            </Box>
          ))}
        </Stack>
      </Grid>
    </Grid>
  );
}

function NumericInterpretationAlerts({ result }) {
  const asymmetric = result.std && Math.abs(result.average - result.median) > 0.5 * result.std;
  return (
    <Stack spacing={1} sx={{ mb: 2 }}>
      <Alert severity="info">
        Среднее показывает общий уровень признака, медиана - типичное значение.
         {/* IQR - разброс центральных 50% наблюдений. */}
      </Alert>
      {asymmetric && (
        <Alert severity="warning">
          Среднее и медиана заметно различаются; распределение может быть асимметричным или содержать выбросы.
        </Alert>
      )}
      {/* {hasOutliers && (
        <Alert severity="warning">
          Обнаружены выбросы по правилу IQR; проверьте, являются ли они ошибками ввода или содержательно важными наблюдениями.
        </Alert>
      )} */}
    </Stack>
  );
}

function TextAnalytics({ question }) {
  const result = question.result ?? {};
  const texts = result.text_answers ?? [];

  return (
    <Box>
      <Typography variant="body2" sx={{ mb: 2 }}>
        Текстовых ответов: <strong>{result.total_text_answers ?? 0}</strong>
      </Typography>

      {texts.length ? (
        <Stack spacing={1}>
          {texts.map((text, index) => (
            <Typography key={`${text}-${index}`} color="text.secondary" variant="body2">
              {text}
            </Typography>
          ))}
        </Stack>
      ) : (
        <Typography color="text.secondary" variant="body2">
          Текстовых ответов пока нет.
        </Typography>
      )}
    </Box>
  );
}

function ScaleAnalytics({ question }) {
  const result = question.result ?? {};
  const distribution = result.distribution ?? [];

  return (
    <Box>
      <NumericInterpretationAlerts result={result} />
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} md={3}>
          <Metric label="Наблюдений" value={formatNumber(result.n ?? result.answered_count)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Пропусков" value={`${formatNumber(result.missing_count)} (${formatNumber(result.missing_rate)}%)`} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Среднее" value={formatNumber(result.average)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Медиана" value={formatNumber(result.median)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Минимум" value={formatNumber(result.min)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Максимум" value={formatNumber(result.max)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Стандартное отклонение" value={formatNumber(result.std)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Дисперсия" value={formatNumber(result.variance)} />
        </Grid>
        {/* <Grid item xs={6} md={3}>
          <Metric label="Q1 / Q3" value={`${formatNumber(result.q1)} / ${formatNumber(result.q3)}`} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="IQR" value={formatNumber(result.iqr)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Выбросы по IQR" value={formatNumber(result.outliers?.count)} />
        </Grid> */}
      </Grid>

      {distribution.length ? (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <BarChart width={BAR_CHART_WIDTH} height={CHART_HEIGHT} data={distribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="value" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" name="Ответов" fill="#27ae60" />
          </BarChart>
        </Box>
      ) : (
        <Typography color="text.secondary" variant="body2">
          Числовых ответов пока нет.
        </Typography>
      )}
    </Box>
  );
}

function NumberAnalytics({ question }) {
  const result = question.result ?? {};
  const distribution = result.distribution ?? [];

  return (
    <Box>
      <NumericInterpretationAlerts result={result} />
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} md={3}>
          <Metric label="Наблюдений" value={formatNumber(result.n ?? result.answered_count)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Пропусков" value={`${formatNumber(result.missing_count)} (${formatNumber(result.missing_rate)}%)`} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Среднее" value={formatNumber(result.average)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Медиана" value={formatNumber(result.median)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Минимум" value={formatNumber(result.min)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Максимум" value={formatNumber(result.max)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Стандартное отклонение" value={formatNumber(result.std)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Дисперсия" value={formatNumber(result.variance)} />
        </Grid>
        {/* <Grid item xs={6} md={3}>
          <Metric label="Q1 / Q3" value={`${formatNumber(result.q1)} / ${formatNumber(result.q3)}`} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="IQR" value={formatNumber(result.iqr)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <Metric label="Выбросы по IQR" value={formatNumber(result.outliers?.count)} />
        </Grid> */}
      </Grid>

      {distribution.length ? (
        <Box sx={{ width: "100%", overflowX: "auto" }}>
          <BarChart width={BAR_CHART_WIDTH} height={CHART_HEIGHT} data={distribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="value" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" name="Ответов" fill="#27ae60" />
          </BarChart>
        </Box>
      ) : (
        <Typography color="text.secondary" variant="body2">
          Числовых ответов пока нет.
        </Typography>
      )}
    </Box>
  );
}

function DateAnalytics({ question }) {
  const result = question.result ?? {};
  const dates = result.text_answers ?? [];
  const distribution = Object.values(
    dates.reduce((acc, date) => {
      acc[date] = acc[date] || { value: date, count: 0 };
      acc[date].count += 1;
      return acc;
    }, {})
  ).sort((a, b) => String(a.value).localeCompare(String(b.value)));

  return (
    <Box>
      <Typography variant="body2" sx={{ mb: 2 }}>
        Ответов с датой: <strong>{result.total_text_answers ?? 0}</strong>
      </Typography>

      {distribution.length ? (
        <>
          <Box sx={{ mb: 2, width: "100%", overflowX: "auto" }}>
            <BarChart width={BAR_CHART_WIDTH} height={CHART_HEIGHT} data={distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="value" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" name="Ответов" fill="#56ccf2" />
            </BarChart>
          </Box>

          <Stack spacing={1}>
            {distribution.map(item => (
              <Stack key={item.value} direction="row" justifyContent="space-between" spacing={2}>
                <Typography>{item.value}</Typography>
                <Typography color="text.secondary">{item.count}</Typography>
              </Stack>
            ))}
          </Stack>
        </>
      ) : (
        <Typography color="text.secondary" variant="body2">
          Ответов с датой пока нет.
        </Typography>
      )}
    </Box>
  );
}

function MatrixAnalytics({ question }) {
  const rows = question.result?.rows ?? [];
  const columns = rows[0]?.columns ?? [];

  if (!rows.length || !columns.length) {
    return (
      <Typography color="text.secondary" variant="body2">
        Данных по матрице пока нет.
      </Typography>
    );
  }

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Строка</TableCell>
            {columns.map(column => (
              <TableCell key={column.id} align="center">
                {column.text}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map(row => (
            <TableRow key={row.id}>
              <TableCell component="th" scope="row">
                {row.text}
              </TableCell>
              {row.columns.map(column => (
                <TableCell key={column.id} align="center" sx={{ bgcolor: `rgba(47, 128, 237, ${Math.min((column.percent_shown ?? 0) / 100, 0.65)})` }}>
                  <Typography>{column.count}</Typography>
                  <Typography color="text.secondary" variant="caption">
                    {column.percent_answered_row ?? column.percent_answered}% от ответивших по строке / {column.percent_shown ?? column.percent_answered}% от видевших
                  </Typography>
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

function MatrixMultiAnalytics({ question }) {
  const rows = question.result?.rows ?? [];
  const columns = question.result?.columns ?? [];
  const cells = question.result?.cells ?? [];
  const rowSummary = question.result?.row_summary ?? [];
  const columnSummary = question.result?.column_summary ?? [];
  const cellsByKey = new Map(cells.map((cell) => [`${cell.row_id}:${cell.column_id}`, cell]));
  const wrapCellSx = { whiteSpace: "normal", overflowWrap: "anywhere", minWidth: 140 };

  if (!rows.length || !columns.length) {
    return (
      <Typography color="text.secondary" variant="body2">
        Р”Р°РЅРЅС‹С… РїРѕ РјР°С‚СЂРёС†Рµ РїРѕРєР° РЅРµС‚.
      </Typography>
    );
  }

  return (
    <Stack spacing={3}>
      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={wrapCellSx}>Row</TableCell>
              {columns.map(column => (
                <TableCell key={column.id} align="center" sx={wrapCellSx}>
                  {column.text}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map(row => (
              <TableRow key={row.id}>
                <TableCell component="th" scope="row" sx={wrapCellSx}>
                  {row.text}
                </TableCell>
                {columns.map(column => {
                  const cell = cellsByKey.get(`${row.id}:${column.id}`) || {};
                  return (
                    <TableCell key={column.id} align="center" sx={{ ...wrapCellSx, bgcolor: `rgba(47, 128, 237, ${Math.min((cell.percent_shown ?? 0) / 100, 0.65)})` }}>
                      <Typography>{cell.count ?? 0}</Typography>
                      <Typography color="text.secondary" variant="caption" component="div">
                        {formatNumber(cell.percent_answered_row ?? cell.percent_answered ?? 0)}% от ответивших по строке
                      </Typography>
                      <Typography color="text.secondary" variant="caption" component="div">
                        {formatNumber(cell.percent_shown ?? cell.percent_answered ?? 0)}% от видевших
                      </Typography>
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Divider />

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Row Summary
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={wrapCellSx}>Row</TableCell>
              <TableCell align="right">Selected total</TableCell>
              <TableCell align="right">Respondents</TableCell>
              <TableCell align="right">% respondents</TableCell>
              <TableCell align="right">Avg selected</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rowSummary.map(row => (
              <TableRow key={row.row_id}>
                <TableCell sx={wrapCellSx}>{row.row_text}</TableCell>
                <TableCell align="right">{row.selected_total ?? 0}</TableCell>
                <TableCell align="right">{row.respondent_count ?? 0}</TableCell>
                <TableCell align="right">{formatNumber(row.respondent_share ?? 0)}%</TableCell>
                <TableCell align="right">{formatNumber(row.avg_selected_per_respondent ?? 0)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ width: "100%", overflowX: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Column Summary
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={wrapCellSx}>Column</TableCell>
              <TableCell align="right">Selected total</TableCell>
              <TableCell align="right">Respondents</TableCell>
              <TableCell align="right">% respondents</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {columnSummary.map(column => (
              <TableRow key={column.column_id}>
                <TableCell sx={wrapCellSx}>{column.column_text}</TableCell>
                <TableCell align="right">{column.selected_total ?? 0}</TableCell>
                <TableCell align="right">{column.respondent_count ?? 0}</TableCell>
                <TableCell align="right">{formatNumber(column.respondent_share ?? 0)}%</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Stack>
  );
}

function RankingAnalytics({ question }) {
  const options = question.result?.options ?? [];

  if (!options.length) {
    return (
      <Typography color="text.secondary" variant="body2">
        Данных по ранжированию пока нет.
      </Typography>
    );
  }

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Вариант</TableCell>
            <TableCell align="center">Среднее место</TableCell>
            <TableCell align="center">Первое место</TableCell>
            <TableCell align="center">Медианный ранг</TableCell>
            <TableCell align="center">Последнее место</TableCell>
            <TableCell>Распределение мест</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {options.map(option => (
            <TableRow key={option.id}>
              <TableCell component="th" scope="row">
                {option.text}
              </TableCell>
              <TableCell align="center">
                {formatNumber(option.average_rank)}
              </TableCell>
              <TableCell align="center">
                {option.first_place_count ?? 0}
              </TableCell>
              <TableCell align="center">{formatNumber(option.median_rank)}</TableCell>
              <TableCell align="center">{option.last_place_count ?? 0}</TableCell>
              <TableCell>
                {(option.rank_distribution || []).length
                  ? option.rank_distribution
                      .map(item => `${item.rank}: ${item.count}`)
                      .join("; ")
                  : "Нет данных"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

function QuestionResult({ question }) {
  if (["single", "multi", "dropdown", "yesno"].includes(question.qtype)) {
    return <ChoiceAnalytics question={question} />;
  }

  if (question.qtype === "text") {
    return <TextAnalytics question={question} />;
  }

  if (question.qtype === "scale") {
    return <ScaleAnalytics question={question} />;
  }

  if (question.qtype === "number") {
    return <NumberAnalytics question={question} />;
  }

  if (question.qtype === "date") {
    return <DateAnalytics question={question} />;
  }

  if (question.qtype === "matrix_single") {
    return <MatrixAnalytics question={question} />;
  }

  if (question.qtype === "matrix_multi") {
    return <MatrixMultiAnalytics question={question} />;
  }

  if (question.qtype === "ranking") {
    return <RankingAnalytics question={question} />;
  }

  return (
    <Typography color="text.secondary" variant="body2">
      {question.result?.message ?? "Для этого типа вопроса аналитика пока не настроена."}
    </Typography>
  );
}

export default function SurveyAnalyticsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [snapshotDialogOpen, setSnapshotDialogOpen] = useState(false);
  const [snapshotTitle, setSnapshotTitle] = useState(getDefaultSnapshotTitle);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState("current");
  const [snapshotError, setSnapshotError] = useState("");
  const [isSavingSnapshot, setIsSavingSnapshot] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState("xlsx");
  const [selectedExportAnalyticResultId, setSelectedExportAnalyticResultId] = useState("");
  const [selectedExportAnalysisReportId, setSelectedExportAnalysisReportId] = useState("");
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteResponsesDialogOpen, setDeleteResponsesDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const { data: survey } = useQuery({
    queryKey: ["survey", id],
    queryFn: () => fetchAdminSurveyById(id),
  });

  const { data: analyticsData } = useQuery({
    queryKey: ["survey-analytics", id],
    enabled: !!id,
    queryFn: () => fetchSurveyAnalytics(id),
  });

  const { data: snapshots = [], refetch: refetchSnapshots } = useQuery({
    queryKey: ["analytic-results", id],
    enabled: !!id,
    queryFn: () => fetchAnalyticResults(id),
  });

  const { data: analysisReports = [] } = useQuery({
    queryKey: ["analysis-reports"],
    queryFn: fetchAnalysisReports,
  });

  const { data: selectedSnapshot } = useQuery({
    queryKey: ["analytic-result", selectedSnapshotId],
    enabled: selectedSnapshotId !== "current",
    queryFn: () => fetchAnalyticResultById(selectedSnapshotId),
  });

  const handleOpenSnapshotDialog = () => {
    setSnapshotTitle(getDefaultSnapshotTitle());
    setSnapshotError("");
    setSnapshotDialogOpen(true);
  };

  const handleSaveSnapshot = async () => {
    setSnapshotError("");
    setIsSavingSnapshot(true);

    try {
      const createdSnapshot = await createAnalyticResult({
        survey_id: Number(id),
        title: snapshotTitle,
      });
      await refetchSnapshots();
      setSelectedSnapshotId(createdSnapshot.id);
      setSnapshotDialogOpen(false);
    } catch (error) {
      setSnapshotError(error.message || "Не удалось сохранить срез аналитики.");
    } finally {
      setIsSavingSnapshot(false);
    }
  };

  const surveyAnalysisReports = analysisReports.filter((report) => Number(report.survey) === Number(id));

  const handleOpenExportDialog = () => {
    setExportError("");
    setSelectedExportAnalyticResultId(snapshots[0]?.id || "");
    setSelectedExportAnalysisReportId(surveyAnalysisReports[0]?.id || "");
    setExportDialogOpen(true);
  };

  const handleExport = async () => {
    if (!selectedExportAnalyticResultId || !selectedExportAnalysisReportId) {
      setExportError("Выберите срез общей аналитики и сложный аналитический отчёт.");
      return;
    }

    const exportByFormat = {
      csv: exportAnalyticsCsv,
      xlsx: exportAnalyticsXlsx,
      pdf: exportAnalyticsPdf,
    };
    const exportFile = exportByFormat[exportFormat];

    setExportError("");
    setIsExporting(true);
    try {
      const blob = await exportFile({
        survey_id: Number(id),
        analytic_result_id: Number(selectedExportAnalyticResultId),
        analysis_report_id: Number(selectedExportAnalysisReportId),
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analytics_report_${id}.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setExportDialogOpen(false);
    } catch (error) {
      setExportError(error.message || `Ошибка экспорта ${exportFormat.toUpperCase()}.`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleConfirmSurveyDeletion = () => {
    setDeleteError("");
    setDeleteDialogOpen(false);
    setDeleteResponsesDialogOpen(true);
  };

  const handleDeleteSurvey = async (deleteResponses) => {
    setDeleteError("");
    setIsDeleting(true);

    try {
      await deleteSurvey(id, deleteResponses);
      await queryClient.invalidateQueries({ queryKey: ["admin-surveys"] });
      await queryClient.invalidateQueries({ queryKey: ["allSurveys"] });
      await queryClient.invalidateQueries({ queryKey: ["surveys"] });
      navigate("/analytics/surveys");
    } catch (error) {
      setDeleteError(error.message || "Не удалось удалить опрос.");
    } finally {
      setIsDeleting(false);
    }
  };

  if (!survey || !analyticsData) return null;

  const displayedAnalyticsData = selectedSnapshotId === "current"
    ? analyticsData
    : selectedSnapshot?.data;

  if (!displayedAnalyticsData) return null;

  const questions = displayedAnalyticsData.questions ?? [];
  const summary = displayedAnalyticsData.summary ?? {};
  const screening = displayedAnalyticsData.screening ?? {};

  return (
    <Container maxWidth={false} sx={{ mt: 4, width: "80%" }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Аналитика: {displayedAnalyticsData.survey?.title ?? survey.title}
      </Typography>

      {survey.description && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {survey.description}
        </Typography>
      )}

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
        <Button variant="contained" onClick={() => navigate(`/analytics/surveys/${survey.id}/responses`)}>
          Ответы
        </Button>
        <Button variant="contained" onClick={() => navigate(`/analytics/surveys/${survey.id}/report-builder`)}>
          Конструктор отчёта
        </Button>
        <Button variant="contained" onClick={handleOpenSnapshotDialog}>
          Сохранить срез аналитики
        </Button>
        <Button variant="outlined" onClick={handleOpenExportDialog}>Экспорт</Button>
        <Button
          color="error"
          variant="outlined"
          onClick={() => {
            setDeleteError("");
            setDeleteDialogOpen(true);
          }}
        >
          Удалить опрос
        </Button>
      </Stack>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ xs: "stretch", md: "center" }}>
            <Typography variant="h6" sx={{ minWidth: 190 }}>
              Сохранённые версии
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Версия аналитики</InputLabel>
              <Select
                label="Версия аналитики"
                value={selectedSnapshotId}
                onChange={(event) => setSelectedSnapshotId(event.target.value)}
              >
                <MenuItem value="current">Текущая аналитика</MenuItem>
                {snapshots.map((snapshot) => (
                  <MenuItem key={snapshot.id} value={snapshot.id}>
                    Сохранённый срез: {snapshot.title || `#${snapshot.id}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </CardContent>
      </Card>

      <Dialog open={snapshotDialogOpen} onClose={() => setSnapshotDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Сохранить срез аналитики</DialogTitle>
        <DialogContent>
          {snapshotError && <Alert severity="error" sx={{ mb: 2 }}>{snapshotError}</Alert>}
          <TextField
            autoFocus
            fullWidth
            label="Название версии"
            value={snapshotTitle}
            onChange={(event) => setSnapshotTitle(event.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSnapshotDialogOpen(false)}>
            Отмена
          </Button>
          <Button
            variant="contained"
            disabled={isSavingSnapshot || !snapshotTitle.trim()}
            onClick={handleSaveSnapshot}
          >
            {isSavingSnapshot ? "Сохранение..." : "Сохранить"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={exportDialogOpen} onClose={() => setExportDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Экспорт аналитики</DialogTitle>
        <DialogContent>
          {exportError && <Alert severity="error" sx={{ mb: 2 }}>{exportError}</Alert>}

          {!snapshots.length && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Сначала сохраните срез общей аналитики.
            </Alert>
          )}

          {!surveyAnalysisReports.length && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Сначала сформируйте отчёт в конструкторе.
            </Alert>
          )}

          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Тип файла</InputLabel>
              <Select
                label="Тип файла"
                value={exportFormat}
                onChange={(event) => setExportFormat(event.target.value)}
              >
                <MenuItem value="xlsx">Excel (XLSX)</MenuItem>
                <MenuItem value="csv">CSV</MenuItem>
                <MenuItem value="pdf">PDF</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth disabled={!snapshots.length}>
              <InputLabel>Срез общей аналитики</InputLabel>
              <Select
                label="Срез общей аналитики"
                value={selectedExportAnalyticResultId}
                onChange={(event) => setSelectedExportAnalyticResultId(event.target.value)}
              >
                {snapshots.map((snapshot) => (
                  <MenuItem key={snapshot.id} value={snapshot.id}>
                    {snapshot.title || `Срез #${snapshot.id}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth disabled={!surveyAnalysisReports.length}>
              <InputLabel>Сложный аналитический отчёт</InputLabel>
              <Select
                label="Сложный аналитический отчёт"
                value={selectedExportAnalysisReportId}
                onChange={(event) => setSelectedExportAnalysisReportId(event.target.value)}
              >
                {surveyAnalysisReports.map((report) => (
                  <MenuItem key={report.id} value={report.id}>
                    {report.title || `Отчёт #${report.id}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialogOpen(false)}>
            Отмена
          </Button>
          <Button
            variant="contained"
            disabled={isExporting || !snapshots.length || !surveyAnalysisReports.length}
            onClick={handleExport}
          >
            {isExporting ? "Формирование..." : `Скачать ${exportFormat.toUpperCase()}`}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Удалить опрос?</DialogTitle>
        <DialogContent>
          <Typography>
            Опрос «{survey.title}» будет удалён из пользовательского списка и аналитики.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>
            Отмена
          </Button>
          <Button color="error" variant="contained" onClick={handleConfirmSurveyDeletion}>
            Продолжить
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteResponsesDialogOpen}
        onClose={() => !isDeleting && setDeleteResponsesDialogOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Удалить ответы на этот опрос?</DialogTitle>
        <DialogContent>
          {deleteError && <Alert severity="error" sx={{ mb: 2 }}>{deleteError}</Alert>}
          <Typography>
            При удалении ответов опрос будет удалён окончательно. Если сохранить ответы,
            опрос получит статус «Удалён» и его можно будет восстановить в управлении опросами.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button disabled={isDeleting} onClick={() => setDeleteResponsesDialogOpen(false)}>
            Отмена
          </Button>
          <Button
            disabled={isDeleting}
            variant="outlined"
            onClick={() => handleDeleteSurvey(false)}
          >
            Сохранить ответы
          </Button>
          <Button
            color="error"
            disabled={isDeleting}
            variant="contained"
            onClick={() => handleDeleteSurvey(true)}
          >
            {isDeleting ? "Удаление..." : "Удалить ответы и опрос"}
          </Button>
        </DialogActions>
      </Dialog>

      <EnhancedSummaryBlock summary={summary} />
      <ScreeningBlock screening={screening} />

      <Typography variant="h5" sx={{ mb: 2 }}>
        Вопросы
      </Typography>

      {questions.length === 0 && (
        <Typography color="text.secondary">
          Для этого опроса пока нет вопросов.
        </Typography>
      )}

      {questions.map((question, index) => (
        <Card key={question.id} sx={{ mb: 4 }}>
          <CardContent>
            <Stack
              direction={{ xs: "column", md: "row" }}
              justifyContent="space-between"
              spacing={2}
              sx={{ mb: 2 }}
            >
              <Box>
                <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
                  Вопрос {index + 1}
                </Typography>
                <Typography variant="h6">{question.text}</Typography>
              </Box>
              <Chip
                label={QUESTION_TYPE_LABELS[question.qtype] ?? question.qtype}
                sx={{ alignSelf: { xs: "flex-start", md: "center" } }}
              />
            </Stack>

            <QuestionBase base={question.base} />

            {question.qtype === "multi" && (
              <Typography color="text.secondary" variant="body2" sx={{ mb: 2 }}>
                Для множественного выбора проценты считаются от числа ответивших, поэтому сумма может быть больше 100%.
              </Typography>
            )}

            <Divider sx={{ mb: 2 }} />

            <QuestionResult question={question} />
          </CardContent>
        </Card>
      ))}
    </Container>
  );
}
