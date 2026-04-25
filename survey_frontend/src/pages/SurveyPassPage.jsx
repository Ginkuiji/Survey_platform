import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { DndContext, closestCenter } from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { fetchSurveyById, startSurvey, submitSurvey } from "../api/surveys";
import {
  getJumpTargetPageId,
  getSurveyQuestions,
  getTerminateCondition,
  getVisiblePages,
} from "../utils/branching";
import {
  Container,
  Typography,
  TextField,
  Radio,
  RadioGroup,
  FormControlLabel,
  Button,
  Box,
  Slider,
  Checkbox,
  LinearProgress,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";

function SortableRankingItem({ option, rank }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: option.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition
  };

  return (
    <Box
      ref={setNodeRef}
      style={style}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        mb: 1,
        p: 1.5,
        border: "1px solid",
        borderColor: isDragging ? "primary.main" : "divider",
        borderRadius: 1,
        bgcolor: "background.paper",
        opacity: isDragging ? 0.75 : 1
      }}
    >
      <Box
        sx={{
          minWidth: 32,
          height: 32,
          borderRadius: 1,
          bgcolor: "action.hover",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 600
        }}
      >
        {rank}
      </Box>

      <Typography sx={{ flex: 1 }}>{option.text}</Typography>

      <Box
        component="button"
        type="button"
        {...attributes}
        {...listeners}
        sx={{
          border: 0,
          bgcolor: "transparent",
          cursor: "grab",
          display: "flex",
          alignItems: "center",
          color: "text.secondary",
          p: 0.5
        }}
      >
        <DragIndicatorIcon />
      </Box>
    </Box>
  );
}

function shuffleItems(items) {
  return [...items]
    .map(item => ({ item, sort: Math.random() }))
    .sort((a, b) => a.sort - b.sort)
    .map(({ item }) => item);
}

function buildPages(survey) {
  const pages = survey.pages?.length
    ? survey.pages
    : [
        {
          id: "page-default",
          title: "",
          description: "",
          order: 0,
          randomize_questions: false,
          questions: survey.questions || []
        }
      ];

  const orderedPages = [...pages].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  const displayPages = survey.randomize_pages ? shuffleItems(orderedPages) : orderedPages;

  return displayPages.map(page => {
    const orderedQuestions = [...(page.questions || [])]
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      .map(question => {
        const orderedOptions = [...(question.options || [])]
          .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
        const orderedRows = [...(question.matrix_rows || [])]
          .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
        const orderedColumns = [...(question.matrix_columns || [])]
          .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

        return {
          ...question,
          options: question.randomize_options ? shuffleItems(orderedOptions) : orderedOptions,
          matrix_rows: orderedRows,
          matrix_columns: orderedColumns
        };
      });

    return {
      ...page,
      questions: page.randomize_questions ? shuffleItems(orderedQuestions) : orderedQuestions
    };
  });
}

function getRankingOrder(question, answer) {
  const optionIds = question.options.map(option => option.id);
  const rankedIds = [...(answer?.ranking_items || [])]
    .sort((a, b) => a.rank - b.rank)
    .map(item => item.option)
    .filter(optionId => optionIds.includes(optionId));
  const missingIds = optionIds.filter(optionId => !rankedIds.includes(optionId));

  return [...rankedIds, ...missingIds];
}

function buildRankingItems(order) {
  return order.map((optionId, index) => ({
    option: optionId,
    rank: index + 1
  }));
}

export default function SurveyPassPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const { data: survey } = useQuery({
    queryKey: ["survey-pass", id],
    queryFn: () => fetchSurveyById(id)
  });

  const [answers, setAnswers] = useState({});
  const [responseToken, setResponseToken] = useState(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [screeningResult, setScreeningResult] = useState(null);

  const pages = useMemo(() => (survey ? buildPages(survey) : []), [survey]);
  const conditions = survey?.conditions || [];
  const visiblePages = useMemo(
    () => getVisiblePages(pages, conditions, answers),
    [pages, conditions, answers]
  );
  const questionsById = useMemo(
    () => Object.fromEntries(getSurveyQuestions(pages).map(question => [question.id, question])),
    [pages]
  );
  const currentPage = visiblePages[pageIndex];
  const isLastPage = pageIndex === visiblePages.length - 1;
  const progress = visiblePages.length ? ((pageIndex + 1) / visiblePages.length) * 100 : 0;

  useEffect(() => {
    if (pageIndex > 0 && pageIndex >= visiblePages.length) {
      setPageIndex(Math.max(visiblePages.length - 1, 0));
    }
  }, [pageIndex, visiblePages.length]);

  const startMutation = useMutation({
    mutationFn: () => startSurvey(id),
    onSuccess: (data) => setResponseToken(data.response_token)
  });

  const submitMutation = useMutation({
    mutationFn: (payload) => submitSurvey(payload),
    onSuccess: (data) => {
      if (data.status === "screened_out") {
        setScreeningResult(data);
        return;
      }
      alert("Ответы отправлены");
      navigate("/");
    }
  });

  const handleChange = (questionId, data) => {
    setAnswers((prev) => ({ ...prev, [questionId]: data }));
  };

  const handleMatrixSingleChange = (questionId, rowId, columnId) => {
    const currentCells = answers[questionId]?.matrix_cells || [];
    handleChange(questionId, {
      matrix_cells: [
        ...currentCells.filter(cell => cell.row !== rowId),
        { row: rowId, column: columnId }
      ]
    });
  };

  const handleMatrixMultiChange = (questionId, rowId, columnId, checked) => {
    const currentCells = answers[questionId]?.matrix_cells || [];
    const nextCells = checked
      ? [...currentCells, { row: rowId, column: columnId }]
      : currentCells.filter(cell => !(cell.row === rowId && cell.column === columnId));

    handleChange(questionId, { matrix_cells: nextCells });
  };

  const handleRankingDragEnd = question => event => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const order = getRankingOrder(question, answers[question.id]);
    const oldIndex = order.indexOf(active.id);
    const newIndex = order.indexOf(over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const nextOrder = arrayMove(order, oldIndex, newIndex);
    handleChange(question.id, {
      ranking_items: buildRankingItems(nextOrder)
    });
  };

  const buildSubmitPayload = (token, answerMap) => ({
    response_token: token,
    answers: Object.entries(answerMap).map(([qid, val]) => ({
      question: Number(qid),
      ...val
    }))
  });

  const handleSubmit = async (answersOverride = null) => {
    let token = responseToken;

    if (!token) {
      const res = await startMutation.mutateAsync();
      token = res.response_token;
    }

    const safeAnswersOverride = answersOverride && !answersOverride?.nativeEvent
      ? answersOverride
      : null;
    const answerMap = { ...(safeAnswersOverride || answers) };
    visiblePages
      .flatMap(page => page.questions || [])
      .filter(question => question.qtype === "ranking")
      .forEach(question => {
        answerMap[question.id] = {
          ...(answerMap[question.id] || {}),
          ranking_items: buildRankingItems(getRankingOrder(question, answerMap[question.id]))
        };
      });

    submitMutation.mutate(buildSubmitPayload(token, answerMap));
  };

  const handleNext = () => {
    const terminateCondition = getTerminateCondition(conditions, answers, questionsById);
    if (terminateCondition) {
      handleSubmit();
      return;
    }

    const targetPageId = getJumpTargetPageId(conditions, answers, questionsById);
    if (targetPageId) {
      const targetIndex = visiblePages.findIndex(page => page.id === targetPageId);
      if (targetIndex >= 0) {
        setPageIndex(targetIndex);
        return;
      }
    }

    setPageIndex(prev => Math.min(prev + 1, visiblePages.length - 1));
  };

  const renderQuestion = q => (
    <Box key={q.id} sx={{ mb: 4 }}>
      <Typography variant="h6">{q.text}</Typography>

      {q.qtype === "dropdown" && (
        <TextField
          select
          fullWidth
          sx={{ mt: 1 }}
          value={answers[q.id]?.selected_options?.[0] || ""}
          SelectProps={{ displayEmpty: true }}
          onChange={(e) =>
            handleChange(q.id, {
              selected_options: [Number(e.target.value)]
            })
          }
        >
          <MenuItem value="" disabled>
            {q.qsettings?.placeholder || "Выберите вариант"}
          </MenuItem>
          {q.options.map((opt) => (
            <MenuItem key={opt.id} value={opt.id}>
              {opt.text}
            </MenuItem>
          ))}
        </TextField>
      )}

      {q.qtype === "yesno" && (
        <RadioGroup
          sx={{ mt: 1 }}
          value={answers[q.id]?.selected_options?.[0] || ""}
          onChange={(e) =>
            handleChange(q.id, {
              selected_options: [Number(e.target.value)]
            })
          }
        >
          {q.options.map((opt) => (
            <FormControlLabel
              key={opt.id}
              value={opt.id}
              control={<Radio />}
              label={opt.text}
            />
          ))}
        </RadioGroup>
      )}

      {q.qtype === "number" && (
        <TextField
          fullWidth
          type="number"
          sx={{ mt: 1 }}
          value={answers[q.id]?.num ?? ""}
          onChange={(e) =>
            handleChange(q.id, {
              num: e.target.value === "" ? null : Number(e.target.value)
            })
          }
          inputProps={{
            min: q.qsettings?.min === "" ? undefined : q.qsettings?.min,
            max: q.qsettings?.max === "" ? undefined : q.qsettings?.max,
            step: q.qsettings?.integer ? 1 : "any",
          }}
        />
      )}

      {q.qtype === "date" && (
        <TextField
          fullWidth
          type="date"
          sx={{ mt: 1 }}
          value={answers[q.id]?.text || ""}
          onChange={(e) =>
            handleChange(q.id, { text: e.target.value })
          }
          InputLabelProps={{ shrink: true }}
          inputProps={{
            min: q.qsettings?.min || undefined,
            max: q.qsettings?.max || undefined,
          }}
        />
      )}

      {q.qtype === "text" && (
        <TextField
          fullWidth
          sx={{ mt: 1 }}
          value={answers[q.id]?.text || ""}
          onChange={(e) =>
            handleChange(q.id, { text: e.target.value })
          }
        />
      )}

      {q.qtype === "single" && (
        <RadioGroup
          sx={{ mt: 1 }}
          value={answers[q.id]?.selected_options?.[0] || ""}
          onChange={(e) =>
            handleChange(q.id, {
              selected_options: [Number(e.target.value)]
            })
          }
        >
          {q.options.map((opt) => (
            <FormControlLabel
              key={opt.id}
              value={opt.id}
              control={<Radio />}
              label={opt.text}
            />
          ))}
        </RadioGroup>
      )}

      {q.qtype === "multi" && (
        <Box sx={{ mt: 1 }}>
          {q.options.map((opt) => {
            const current = answers[q.id]?.selected_options || [];
            const checked = current.includes(opt.id);

            return (
              <FormControlLabel
                key={opt.id}
                control={
                  <Checkbox
                    checked={checked}
                    onChange={(e) => {
                      const updated = e.target.checked
                        ? [...current, opt.id]
                        : current.filter((v) => v !== opt.id);
                      handleChange(q.id, {
                        selected_options: updated
                      });
                    }}
                  />
                }
                label={opt.text}
              />
            );
          })}
        </Box>
      )}

      {q.qtype === "scale" && (
        <Slider
          sx={{ mt: 2 }}
          min={q.qsettings?.min ?? 1}
          max={q.qsettings?.max ?? 5}
          step={q.qsettings?.step ?? 1}
          value={answers[q.id]?.num ?? q.qsettings?.min ?? 1}
          onChange={(e, val) =>
            handleChange(q.id, { num: val })
          }
          marks
          valueLabelDisplay="auto"
        />
      )}

      {q.qtype === "ranking" && (
        <Box sx={{ mt: 2 }}>
          <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
            Перетащите варианты в нужном порядке: верхний вариант получит первое место.
          </Typography>

          <DndContext
            collisionDetection={closestCenter}
            onDragEnd={handleRankingDragEnd(q)}
          >
            <SortableContext
              items={getRankingOrder(q, answers[q.id])}
              strategy={verticalListSortingStrategy}
            >
              {getRankingOrder(q, answers[q.id]).map((optionId, index) => {
                const option = q.options.find(item => item.id === optionId);
                if (!option) return null;

                return (
                  <SortableRankingItem
                    key={option.id}
                    option={option}
                    rank={index + 1}
                  />
                );
              })}
            </SortableContext>
          </DndContext>
        </Box>
      )}

      {q.qtype === "matrix_single" && (
        <Box sx={{ mt: 2, overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell />
                {q.matrix_columns.map(column => (
                  <TableCell key={column.id} align="center">
                    {column.text}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {q.matrix_rows.map(row => (
                <TableRow key={row.id}>
                  <TableCell component="th" scope="row">
                    {row.text}
                  </TableCell>
                  {q.matrix_columns.map(column => {
                    const selectedColumn = answers[q.id]?.matrix_cells?.find(
                      cell => cell.row === row.id
                    )?.column;

                    return (
                      <TableCell key={column.id} align="center">
                        <Radio
                          checked={selectedColumn === column.id}
                          onChange={() => handleMatrixSingleChange(q.id, row.id, column.id)}
                        />
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      {q.qtype === "matrix_multi" && (
        <Box sx={{ mt: 2, overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell />
                {q.matrix_columns.map(column => (
                  <TableCell key={column.id} align="center">
                    {column.text}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {q.matrix_rows.map(row => (
                <TableRow key={row.id}>
                  <TableCell component="th" scope="row">
                    {row.text}
                  </TableCell>
                  {q.matrix_columns.map(column => {
                    const checked = (answers[q.id]?.matrix_cells || []).some(
                      cell => cell.row === row.id && cell.column === column.id
                    );

                    return (
                      <TableCell key={column.id} align="center">
                        <Checkbox
                          checked={checked}
                          onChange={e =>
                            handleMatrixMultiChange(q.id, row.id, column.id, e.target.checked)
                          }
                        />
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}
    </Box>
  );

  if (!survey) return null;

  if (screeningResult) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Typography variant="h4" sx={{ mb: 2 }}>
          Опрос завершён
        </Typography>
        <Typography sx={{ mb: 3 }}>
          {screeningResult.message || "Спасибо за участие. По условиям опроса прохождение завершено досрочно."}
        </Typography>
        <Button variant="contained" onClick={() => navigate("/")}>
          На главную
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate(-1)}
        sx={{ mb: 2 }}
      >
        Назад
      </Button>

      <Typography variant="h4">{survey.title}</Typography>
      <Typography sx={{ mb: 3 }}>{survey.description}</Typography>

      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" sx={{ mb: 1 }}>
          Страница {pageIndex + 1} из {visiblePages.length}
        </Typography>
        <LinearProgress variant="determinate" value={progress} />
      </Box>

      {currentPage?.title && (
        <Typography variant="h5" sx={{ mb: 1 }}>
          {currentPage.title}
        </Typography>
      )}

      {currentPage?.description && (
        <Typography sx={{ mb: 3 }}>
          {currentPage.description}
        </Typography>
      )}

      {currentPage?.questions.map(renderQuestion)}

      <Box sx={{ display: "flex", justifyContent: "space-between", mt: 4 }}>
        <Button
          variant="outlined"
          disabled={pageIndex === 0}
          onClick={() => setPageIndex(prev => Math.max(prev - 1, 0))}
        >
          Назад
        </Button>

        {isLastPage ? (
          <Button
            variant="contained"
            onClick={() => handleSubmit()}
            disabled={submitMutation.isPending || startMutation.isPending}
          >
            Отправить ответы
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleNext}
          >
            Далее
          </Button>
        )}
      </Box>
    </Container>
  );
}
