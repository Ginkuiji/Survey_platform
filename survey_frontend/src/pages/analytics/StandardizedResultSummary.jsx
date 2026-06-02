import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "да" : "нет";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(4);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatPercent(value) {
  if (value === null || value === undefined) return "—";
  return `${formatValue(value)}%`;
}

function DataQualityBlock({ dataQuality }) {
  if (!dataQuality) return null;

  const survey = dataQuality.survey || {};
  const dataset = dataQuality.dataset || {};
  const answers = dataQuality.answers || {};
  const variables = dataQuality.variables || {};
  const time = dataQuality.time || {};
  const datasetSize = dataset.dataset_size ?? dataQuality.dataset_size;
  const analysisN = dataset.analysis_n ?? dataQuality.n;
  const issues = [
    ...(variables.zero_variance_variables || []).map((item) => ({
      type: "Нулевая дисперсия",
      label: item.label || item.code,
      value: `${formatValue(item.unique_values_count)} уникальных значений`,
    })),
    ...(variables.high_missing_variables || []).map((item) => ({
      type: "Высокий уровень пропусков",
      label: item.label || item.code,
      value: formatPercent(item.missing_rate),
    })),
    ...(answers.high_missing_questions || []).map((item) => ({
      type: "Пропуски по вопросу",
      label: item.label || item.question_id,
      value: formatPercent(item.missing_rate),
    })),
  ];

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>Качество данных</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip label={`Всего прохождений: ${formatValue(survey.total_started)}`} />
          <Chip label={`Завершено полностью: ${formatValue(survey.total_completed)}`} />
          <Chip label={`Отсечено: ${formatValue(survey.total_screened_out)}`} />
          <Chip label={`Активных незавершенных: ${formatValue(survey.total_active_unfinished)}`} />
          <Chip label={`Размер набора данных: ${formatValue(datasetSize)}`} />
          <Chip label={`Наблюдений в расчете: ${formatValue(analysisN)}`} />
          <Chip label={`Средняя полнота: ${formatPercent(answers.average_completeness_rate)}`} />
          <Chip label={`Вопросов с высокими пропусками: ${formatValue(answers.high_missing_questions_count)}`} />
          <Chip label={`Переменных с нулевой дисперсией: ${formatValue(variables.zero_variance_variables_count)}`} />
          <Chip label={`Слишком быстрых прохождений: ${formatValue(time.too_fast_responses_count)}`} />
        </Stack>

        {(dataQuality.notes || []).map((note) => (
          <Alert severity="info" key={String(note)} sx={{ mt: 1 }}>{String(note)}</Alert>
        ))}

        {!!issues.length && (
          <Box sx={{ mt: 2, overflowX: "auto" }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Проблемные переменные и вопросы</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Тип</TableCell>
                  <TableCell>Переменная или вопрос</TableCell>
                  <TableCell>Значение</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {issues.map((item, index) => (
                  <TableRow key={`${item.type}-${item.label}-${index}`}>
                    <TableCell>{item.type}</TableCell>
                    <TableCell>{item.label}</TableCell>
                    <TableCell>{item.value}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function practicalSeverity(level) {
  if (level === "high") return "success";
  if (level === "limited") return "warning";
  return "info";
}

function confidenceSeverity(level) {
  if (level === "high") return "success";
  if (level === "low") return "warning";
  return "info";
}

function InterpretationBlock({ interpretation }) {
  if (!interpretation) return null;

  const significance = interpretation.statistical_significance;
  const effect = interpretation.effect_interpretation;
  const practical = interpretation.practical_significance;
  const confidence = interpretation.confidence;
  const hasExtendedInterpretation = significance || effect || practical || confidence;
  if (!hasExtendedInterpretation) return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>Интерпретация результата</Typography>
        <Stack spacing={1}>
          {significance?.interpretation && (
            <Alert severity="info">{significance.interpretation}</Alert>
          )}
          {effect?.interpretation && (
            <Alert severity="info">{effect.interpretation}</Alert>
          )}
          {practical?.interpretation && (
            <Alert severity={practicalSeverity(practical.level)}>{practical.interpretation}</Alert>
          )}
          {confidence?.interpretation && (
            <Alert severity={confidenceSeverity(confidence.level)}>{confidence.interpretation}</Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

function DescriptiveProfileBlock({ profile }) {
  if (!profile?.variables?.length) return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>Описательный профиль переменных</Typography>
        {(profile.notes || []).map((note) => (
          <Alert severity="info" key={String(note)} sx={{ mb: 1 }}>{String(note)}</Alert>
        ))}
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Переменная</TableCell>
                <TableCell>Тип</TableCell>
                <TableCell align="right">n</TableCell>
                <TableCell align="right">Пропуски</TableCell>
                <TableCell align="right">Среднее</TableCell>
                <TableCell align="right">Медиана</TableCell>
                <TableCell align="right">Std</TableCell>
                <TableCell align="right">Min / Max</TableCell>
                <TableCell align="right">Q1 / Q3</TableCell>
                <TableCell align="right">IQR</TableCell>
                <TableCell align="right">Выбросы</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {profile.variables.map((variable) => (
                <TableRow key={variable.code}>
                  <TableCell>
                    <Typography>{variable.label || variable.code}</Typography>
                    {(variable.interpretation?.notes || []).map((note) => (
                      <Typography color="text.secondary" variant="caption" component="div" key={note}>
                        {note}
                      </Typography>
                    ))}
                  </TableCell>
                  <TableCell>{variable.kind}</TableCell>
                  <TableCell align="right">{formatValue(variable.n)}</TableCell>
                  <TableCell align="right">{formatValue(variable.missing_count)} ({formatPercent(variable.missing_rate)})</TableCell>
                  <TableCell align="right">{formatValue(variable.mean)}</TableCell>
                  <TableCell align="right">{formatValue(variable.median)}</TableCell>
                  <TableCell align="right">{formatValue(variable.std)}</TableCell>
                  <TableCell align="right">{formatValue(variable.min)} / {formatValue(variable.max)}</TableCell>
                  <TableCell align="right">{formatValue(variable.q1)} / {formatValue(variable.q3)}</TableCell>
                  <TableCell align="right">{formatValue(variable.iqr)}</TableCell>
                  <TableCell align="right">{formatValue(variable.outliers?.count)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function StandardizedResultSummary({ result }) {
  if (!result) return null;

  const indicators = Object.entries(result.main_results || {}).filter(
    ([, value]) => value !== null && value !== undefined && !Array.isArray(value),
  );

  return (
    <Stack spacing={2} sx={{ mb: 3 }}>
      <Box>
        <Typography variant="h6">{result.title}</Typography>
        {result.purpose && <Alert severity="info" sx={{ mt: 1 }}>{result.purpose}</Alert>}
        {result.analysis_type === "regression" && <Alert severity="info" sx={{ mt: 1 }}>Для регрессии важно учитывать качество модели, мультиколлинеарность и диагностику остатков, а не только значимость коэффициентов.</Alert>}
        {result.analysis_type === "logistic_regression" && <Alert severity="info" sx={{ mt: 1 }}>Odds ratio показывает изменение шансов события, а ROC-AUC и матрица ошибок помогают оценить качество классификации.</Alert>}
        {result.analysis_type === "factor_analysis" && <Alert severity="info" sx={{ mt: 1 }}>Факторный анализ помогает определить, можно ли объединить несколько вопросов в скрытые факторы или шкалы. Названия факторов должны задаваться исследователем на основе содержания вопросов с высокими нагрузками.</Alert>}
        {result.analysis_type === "cluster_analysis" && <Alert severity="info" sx={{ mt: 1 }}>Кластерный анализ является разведочным методом. Номера кластеров сами по себе не имеют смысла: кластеры следует интерпретировать по их профилям и отличающим признакам.</Alert>}
      </Box>

      {result.interpretation?.summary && (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1">Краткий вывод</Typography>
            <Typography>{result.interpretation.summary}</Typography>
          </CardContent>
        </Card>
      )}

      <InterpretationBlock interpretation={result.interpretation} />

      <DescriptiveProfileBlock profile={result.descriptive_profile} />

      <DataQualityBlock dataQuality={result.data_quality} />

      {!!indicators.length && (
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>Главные показатели</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {indicators.map(([name, value]) => (
              <Chip key={name} label={`${name}: ${formatValue(value)}`} />
            ))}
          </Stack>
        </Box>
      )}

      {result.effect_size?.name && (
        <Chip
          color="primary"
          variant="outlined"
          label={`${result.effect_size.name}: ${formatValue(result.effect_size.value ?? result.effect_size.values)}${result.effect_size.interpretation ? ` — ${result.effect_size.interpretation}` : ""}`}
        />
      )}

      {(result.warnings || []).map((warning, index) => (
        <Alert severity="warning" key={`${String(warning)}-${index}`}>{String(warning)}</Alert>
      ))}

      {!!result.interpretation?.limitations?.length && (
        <Box>
          <Typography variant="subtitle1">Ограничения интерпретации</Typography>
          <ul>
            {result.interpretation.limitations.map((item) => <li key={String(item)}>{String(item)}</li>)}
          </ul>
        </Box>
      )}

      {!!result.recommendations?.length && (
        <Box>
          <Typography variant="subtitle1">Рекомендации</Typography>
          <ul>
            {result.recommendations.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </Box>
      )}

      {!!result.visualizations?.length && (
        <Box>
          <Typography variant="subtitle1">Рекомендуемые визуализации</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
            {result.visualizations.map((item) => (
              <Chip key={`${item.type}-${item.title}`} label={item.title || item.type} />
            ))}
          </Stack>
        </Box>
      )}
    </Stack>
  );
}
