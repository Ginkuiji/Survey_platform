import { useState } from "react";
import { useNavigate } from "react-router-dom";
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

import { DndContext, closestCenter } from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  verticalListSortingStrategy
} from "@dnd-kit/sortable";

import DeleteIcon from "@mui/icons-material/Delete";
import SortableQuestionCard from "../components/SortableQuestionCard";
import AddQuestionMenu from "../components/AddQuestionMenu";
import BranchingConditionsEditor from "../components/BranchingConditionsEditor";
import {
  createSurvey,
  fetchAdminSurveyById,
  saveSurveyConditions,
  saveSurveyPages,
} from "../api/surveys";
import { createEmptyQuestion } from "../types/survey";
import { buildConditionPayload } from "../utils/branching";

function createEmptyPage(index = 0) {
  return {
    id: `page-new-${Date.now()}-${index}`,
    title: `Страница ${index + 1}`,
    description: "",
    randomize_questions: false,
    questions: []
  };
}

function sortSavedPages(pages = []) {
  return [...pages]
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map(page => ({
      ...page,
      questions: [...(page.questions || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    }));
}

export default function CreateSurveyPage() {
  const navigate = useNavigate();

  const [survey, setSurvey] = useState({
    title: "",
    description: "",
    status: "draft",
    starts_at: "",
    ends_at: "",
    is_anonymous: false,
    randomize_pages: false
  });

  const [pages, setPages] = useState([createEmptyPage(0)]);
  const [conditions, setConditions] = useState([]);

  const handleSurveyChange = (field, value) => {
    setSurvey(prev => ({ ...prev, [field]: value }));
  };

  const updatePage = (pageId, changed) => {
    setPages(prev =>
      prev.map(page => (page.id === pageId ? { ...page, ...changed } : page))
    );
  };

  const addPage = () => {
    setPages(prev => [...prev, createEmptyPage(prev.length)]);
  };

  const deletePage = pageId => {
    setPages(prev => {
      if (prev.length === 1) return prev;
      return prev.filter(page => page.id !== pageId);
    });
  };

  const addQuestion = (pageId, qtype) => {
    setPages(prev =>
      prev.map(page =>
        page.id === pageId
          ? { ...page, questions: [...page.questions, createEmptyQuestion(qtype)] }
          : page
      )
    );
  };

  const updateQuestion = (pageId, questionId, changed) => {
    setPages(prev =>
      prev.map(page =>
        page.id === pageId
          ? {
              ...page,
              questions: page.questions.map(q =>
                q.id === questionId ? { ...q, ...changed } : q
              )
            }
          : page
      )
    );
  };

  const deleteQuestion = (pageId, questionId) => {
    setPages(prev =>
      prev.map(page =>
        page.id === pageId
          ? {
              ...page,
              questions: page.questions.filter(q => q.id !== questionId)
            }
          : page
      )
    );
  };

  const handleDragEnd = pageId => event => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setPages(prev =>
      prev.map(page => {
        if (page.id !== pageId) return page;

        const oldIndex = page.questions.findIndex(q => q.id === active.id);
        const newIndex = page.questions.findIndex(q => q.id === over.id);

        return {
          ...page,
          questions: arrayMove(page.questions, oldIndex, newIndex)
        };
      })
    );
  };

  const handleSave = async () => {
    if (!survey.title.trim()) {
      alert("Введите название опроса");
      return;
    }

    const created = await createSurvey(survey);
    await saveSurveyPages(created.id, pages);
    const savedSurvey = await fetchAdminSurveyById(created.id);
    const savedPages = sortSavedPages(savedSurvey.pages || []);
    const conditionsPayload = conditions
      .map(condition => buildConditionPayload(condition, pages, savedPages))
      .filter(Boolean);
    await saveSurveyConditions(created.id, conditionsPayload);

    alert("Опрос создан");
    navigate(`/admin/surveys/${created.id}`);
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Создание опроса
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <TextField
            label="Название"
            fullWidth
            sx={{ mb: 2 }}
            value={survey.title}
            onChange={e => handleSurveyChange("title", e.target.value)}
          />

          <TextField
            label="Описание"
            fullWidth
            sx={{ mb: 2 }}
            value={survey.description}
            onChange={e => handleSurveyChange("description", e.target.value)}
          />

          <TextField
            select
            label="Статус"
            fullWidth
            sx={{ mb: 2 }}
            value={survey.status}
            onChange={e => handleSurveyChange("status", e.target.value)}
          >
            <MenuItem value="draft">Черновик</MenuItem>
            <MenuItem value="active">Активный</MenuItem>
            <MenuItem value="closed">Закрыт</MenuItem>
          </TextField>

          <TextField
            type="date"
            label="Дата начала"
            fullWidth
            InputLabelProps={{ shrink: true }}
            sx={{ mb: 2 }}
            value={survey.starts_at}
            onChange={e => handleSurveyChange("starts_at", e.target.value)}
          />

          <TextField
            type="date"
            label="Дата окончания"
            fullWidth
            InputLabelProps={{ shrink: true }}
            sx={{ mb: 2 }}
            value={survey.ends_at}
            onChange={e => handleSurveyChange("ends_at", e.target.value)}
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={survey.is_anonymous}
                onChange={e => handleSurveyChange("is_anonymous", e.target.checked)}
              />
            }
            label="Анонимный опрос"
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={survey.randomize_pages}
                onChange={e => handleSurveyChange("randomize_pages", e.target.checked)}
              />
            }
            label="Перемешивать страницы"
          />
        </CardContent>
      </Card>

      <Divider sx={{ mb: 3 }} />

      <BranchingConditionsEditor
        pages={pages}
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

      {pages.map((page, pageIndex) => (
        <Card key={page.id} sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Страница {pageIndex + 1}
              </Typography>

              <IconButton
                color="error"
                disabled={pages.length === 1}
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

              <AddQuestionMenu onAdd={qtype => addQuestion(page.id, qtype)} />
            </Box>
          </CardContent>
        </Card>
      ))}

      <Button variant="contained" size="large" onClick={handleSave}>
        Создать опрос
      </Button>
    </Container>
  );
}
