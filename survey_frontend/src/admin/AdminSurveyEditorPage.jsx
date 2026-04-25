import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import {
  Container,
  Typography,
  TextField,
  Card,
  CardContent,
  Button,
  MenuItem,
  Divider,
  Box,
  IconButton,
  FormControlLabel,
  Checkbox
} from "@mui/material";

import {
  DndContext,
  closestCenter
} from "@dnd-kit/core";

import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove
} from "@dnd-kit/sortable";

import {
  fetchAdminSurveyById,
  updateSurvey,
  saveSurveyPages,
  fetchSurveyResponses,
  createSurvey,
  saveSurveyConditions,
} from "../api/surveys";

import SortableQuestionCard from "../components/SortableQuestionCard";
import AddQuestionMenu from "../components/AddQuestionMenu";
import BranchingConditionsEditor from "../components/BranchingConditionsEditor";
import DeleteIcon from "@mui/icons-material/Delete";
import { createEmptyQuestion } from "../types/survey";
import {
  buildConditionPayload,
  mapServerConditionsToEditor,
  normalizeEditorConditions,
} from "../utils/branching";

function normalizeQuestions(questions = []) {
  return questions.map((q, qIndex) => ({
    text: q.text || "",
    qtype: q.qtype || "",
    required: q.required ?? true,
    qsettings: q.qsettings || {},
    randomize_options: q.randomize_options ?? false,
    order: qIndex,
    options: (q.options || []).map((o, oIndex) => ({
      text: o.text || "",
      value: o.value || "",
      order: oIndex
    })),
    matrix_rows: (q.matrix_rows || []).map((row, rowIndex) => ({
      text: row.text || "",
      value: row.value || "",
      order: rowIndex
    })),
    matrix_columns: (q.matrix_columns || []).map((column, columnIndex) => ({
      text: column.text || "",
      value: column.value || "",
      order: columnIndex
    }))
  }));
}

function normalizePages(pages = []) {
  return pages.map((page, pageIndex) => ({
    title: page.title || "",
    description: page.description || "",
    order: pageIndex,
    randomize_questions: page.randomize_questions ?? false,
    questions: normalizeQuestions(page.questions || [])
  }));
}

function buildPages(data) {
  if (data.pages?.length) {
    return [...data.pages]
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      .map((page, pageIndex) => ({
        ...page,
        id: page.id ?? `page-${pageIndex}`,
        title: page.title || "",
        description: page.description || "",
        randomize_questions: page.randomize_questions ?? false,
        questions: [...(page.questions || [])]
          .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
          .map((q, qIndex) => ({
            ...q,
            id: q.id ?? `question-${pageIndex}-${qIndex}`,
            randomize_options: q.randomize_options ?? false,
            options: [...(q.options || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
            matrix_rows: [...(q.matrix_rows || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
            matrix_columns: [...(q.matrix_columns || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
          }))
      }));
  }

  return [
    {
      id: "page-default",
      title: "Страница 1",
      description: "",
      order: 0,
      randomize_questions: false,
      questions: data.questions || []
    }
  ];
}

export default function AdminSurveyEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [survey, setSurvey] = useState(null);
  const [initialPagesSnapshot, setInitialPagesSnapshot] = useState("[]");
  const [conditions, setConditions] = useState([]);
  const [initialConditionsSnapshot, setInitialConditionsSnapshot] = useState("[]");

  /* -------- загрузка опроса -------- */
  const { data } = useQuery({
    queryKey: ["admin-survey-editor", id],
    queryFn: () => fetchAdminSurveyById(id)
  });

  /* -------- есть ли ответы -------- */
  const { data: responses = [] } = useQuery({
    queryKey: ["survey-responses-check", id],
    queryFn: () => fetchSurveyResponses(id),
    enabled: !!id,
  });

  const hasResponses = responses.length > 0;

  useEffect(() => {
    if (data) {
      const pages = buildPages(data);
      setSurvey({
        ...data,
        randomize_pages: data.randomize_pages ?? false,
        pages
      });
      const editorConditions = mapServerConditionsToEditor(data.conditions || []);
      setConditions(editorConditions);
      setInitialPagesSnapshot(JSON.stringify(normalizePages(pages)));
      setInitialConditionsSnapshot(JSON.stringify(normalizeEditorConditions(editorConditions)));
    }
  }, [data]);


  /* -------- шапка опроса -------- */
  const handleFieldChange = (field, value) => {
    setSurvey(prev => ({ ...prev, [field]: value }));
  };

  /* -------- страницы и вопросы -------- */
  const updatePage = (pageId, changed) => {
    setSurvey(prev => ({
      ...prev,
      pages: prev.pages.map(page =>
        page.id === pageId ? { ...page, ...changed } : page
      )
    }));
  };

  const addPage = () => {
    setSurvey(prev => ({
      ...prev,
      pages: [
        ...prev.pages,
        {
          id: `page-new-${Date.now()}`,
          title: `Страница ${prev.pages.length + 1}`,
          description: "",
          randomize_questions: false,
          questions: []
        }
      ]
    }));
  };

  const deletePage = pageId => {
    setSurvey(prev => {
      if (prev.pages.length === 1) return prev;

      return {
        ...prev,
        pages: prev.pages.filter(page => page.id !== pageId)
      };
    });
  };

  const updateQuestion = (pageId, qid, changed) => {
    setSurvey(prev => ({
      ...prev,
      pages: prev.pages.map(page =>
        page.id === pageId
          ? {
              ...page,
              questions: page.questions.map(q =>
                q.id === qid ? { ...q, ...changed } : q
              )
            }
          : page
      )
    }));
  };

  const deleteQuestion = (pageId, qid) => {
    setSurvey(prev => ({
      ...prev,
      pages: prev.pages.map(page =>
        page.id === pageId
          ? {
              ...page,
              questions: page.questions.filter(q => q.id !== qid)
            }
          : page
      )
    }));
  };

  const addNewQuestion = (pageId, qtype) => {
    setSurvey(prev => ({
      ...prev,
      pages: prev.pages.map(page =>
        page.id === pageId
          ? {
              ...page,
              questions: [...page.questions, createEmptyQuestion(qtype)]
            }
          : page
      )
    }));
  };

  /* -------- drag & drop -------- */
  const handleDragEnd = pageId => event => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setSurvey(prev => {
      return {
        ...prev,
        pages: prev.pages.map(page => {
          if (page.id !== pageId) return page;

          const oldIndex = page.questions.findIndex(q => q.id === active.id);
          const newIndex = page.questions.findIndex(q => q.id === over.id);

          return {
            ...page,
            questions: arrayMove(page.questions, oldIndex, newIndex)
          };
        })
      };
    });
  };

  /* -------- проверка изменения структуры -------- */
  const structureChanged = useMemo(() => {
    if (!survey) return false;
    
    const currentSnapshot = JSON.stringify(normalizePages(survey.pages || []));
    return currentSnapshot !== initialPagesSnapshot;
  }, [survey?.pages, initialPagesSnapshot]);

  const conditionsChanged = useMemo(() => {
    const currentSnapshot = JSON.stringify(normalizeEditorConditions(conditions));
    return currentSnapshot !== initialConditionsSnapshot;
  }, [conditions, initialConditionsSnapshot]);

  const saveConditionsForSurvey = async (surveyId, originalPages, savedPages) => {
    const payload = conditions
      .map(condition => buildConditionPayload(condition, originalPages, savedPages))
      .filter(Boolean);

    await saveSurveyConditions(surveyId, payload);
  };

  const shouldCreateCopy = hasResponses && (structureChanged || conditionsChanged);

  if (!survey) return null;

  /* -------- сохранение -------- */
  const handleSave = async () => {
    if (shouldCreateCopy) {
      const newSurvey = await createSurvey({
        title: `${survey.title} (копия)`,
        description: survey.description,
        status: "draft",
        starts_at: survey.starts_at,
        ends_at: survey.ends_at,
        is_anonymous: survey.is_anonymous,
        randomize_pages: survey.randomize_pages
      });

      await saveSurveyPages(newSurvey.id, survey.pages);
      const savedSurvey = await fetchAdminSurveyById(newSurvey.id);
      await saveConditionsForSurvey(newSurvey.id, survey.pages, buildPages(savedSurvey));

      alert("Создана копия опроса");
      navigate(`/admin/surveys/${newSurvey.id}`);
      return;
    }

    await updateSurvey(id, {
      title: survey.title,
      description: survey.description,
      status: survey.status,
      starts_at: survey.starts_at,
      ends_at: survey.ends_at,
      is_anonymous: survey.is_anonymous,
      randomize_pages: survey.randomize_pages
    });

    await saveSurveyPages(id, survey.pages);
    const savedSurvey = await fetchAdminSurveyById(id);
    await saveConditionsForSurvey(id, survey.pages, buildPages(savedSurvey));

    alert("Опрос обновлён");
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Редактирование опроса
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <TextField
            label="Название"
            fullWidth
            sx={{ mb: 2 }}
            value={survey.title}
            onChange={e => handleFieldChange("title", e.target.value)}
          />

          <TextField
            label="Описание"
            fullWidth
            sx={{ mb: 2 }}
            value={survey.description}
            onChange={e => handleFieldChange("description", e.target.value)}
          />

          <TextField
            select
            label="Статус"
            fullWidth
            sx={{ mb: 2 }}
            value={survey.status}
            onChange={e => handleFieldChange("status", e.target.value)}
          >
            <MenuItem value="draft">Черновик</MenuItem>
            <MenuItem value="active">Активный</MenuItem>
            <MenuItem value="closed">Закрыт</MenuItem>
          </TextField>

          <TextField
            label="Дата начала"
            type="date"
            fullWidth
            sx={{ mb: 2 }}
            value={survey.starts_at || ""}
            InputLabelProps={{ shrink: true }}
            onChange={e => handleFieldChange("starts_at", e.target.value)}
          />

          <TextField
            label="Дата окончания"
            type="date"
            fullWidth
            sx={{ mb: 2 }}
            value={survey.ends_at || ""}
            InputLabelProps={{ shrink: true }}
            onChange={e => handleFieldChange("ends_at", e.target.value)}
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={survey.is_anonymous ?? false}
                onChange={e => handleFieldChange("is_anonymous", e.target.checked)}
              />
            }
            label="Анонимный опрос"
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={survey.randomize_pages ?? false}
                onChange={e => handleFieldChange("randomize_pages", e.target.checked)}
              />
            }
            label="Перемешивать страницы"
          />
        </CardContent>
      </Card>

      <Divider sx={{ mb: 3 }} />

      <BranchingConditionsEditor
        pages={survey.pages}
        conditions={conditions}
        onChange={setConditions}
      />

      <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
        <Typography variant="h5" sx={{ flexGrow: 1 }}>
          Страницы
        </Typography>

        <Button variant="outlined" onClick={addPage}>
          Добавить страницу
        </Button>
      </Box>

      {survey.pages.map((page, pageIndex) => (
        <Card key={page.id} sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Страница {pageIndex + 1}
              </Typography>

              <IconButton
                color="error"
                disabled={survey.pages.length === 1}
                onClick={() => deletePage(page.id)}
              >
                <DeleteIcon />
              </IconButton>
            </Box>

            <TextField
              label="Название страницы"
              fullWidth
              sx={{ mb: 2 }}
              value={page.title}
              onChange={e => updatePage(page.id, { title: e.target.value })}
            />

            <TextField
              label="Описание страницы"
              fullWidth
              multiline
              minRows={2}
              sx={{ mb: 2 }}
              value={page.description}
              onChange={e => updatePage(page.id, { description: e.target.value })}
            />

            <FormControlLabel
              sx={{ mb: 2 }}
              control={
                <Checkbox
                  checked={page.randomize_questions}
                  onChange={e =>
                    updatePage(page.id, { randomize_questions: e.target.checked })
                  }
                />
              }
              label="Перемешивать вопросы на странице"
            />

            <DndContext
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd(page.id)}
            >
              <SortableContext
                items={page.questions.map(q => q.id)}
                strategy={verticalListSortingStrategy}
              >
                {page.questions.map(q => (
                  <SortableQuestionCard
                    key={q.id}
                    question={q}
                    onChange={changed => updateQuestion(page.id, q.id, changed)}
                    onDelete={() => deleteQuestion(page.id, q.id)}
                  />
                ))}
              </SortableContext>
            </DndContext>

            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>
                Добавить вопрос
              </Typography>

              <AddQuestionMenu onAdd={qtype => addNewQuestion(page.id, qtype)} />
            </Box>
          </CardContent>
        </Card>
      ))}

      <Button
        variant="outlined"
        sx={{ mr: 2 }}
        onClick={() => navigate(`/analytics/surveys/${id}/responses`)}
      >
        Посмотреть ответы
      </Button>

      <Button variant="contained" onClick={handleSave}>
        {shouldCreateCopy ? "Создать копию опроса" : "Сохранить изменения"}
      </Button>
    </Container>
  );
}
