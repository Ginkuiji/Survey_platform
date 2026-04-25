import {
  Card,
  CardContent,
  IconButton,
  TextField,
  Typography,
  Box,
  Button,
  FormControlLabel,
  Checkbox
} from "@mui/material";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import DeleteIcon from "@mui/icons-material/Delete";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import { QUESTION_TYPE_OPTIONS, QuestionType } from "../types/survey";

const optionBasedTypes = [
  QuestionType.SINGLE,
  QuestionType.MULTI,
  QuestionType.DROPDOWN,
  QuestionType.RANKING
];

const matrixTypes = [
  QuestionType.MATRIX_SINGLE,
  QuestionType.MATRIX_MULTI
];

function toNumberOrEmpty(value) {
  return value === "" || value === null || value === undefined ? "" : Number(value);
}

export default function SortableQuestionCard({
  question,
  onChange,
  onDelete
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: question.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition
  };

  const typeLabel =
    QUESTION_TYPE_OPTIONS.find(option => option.value === question.qtype)?.label ||
    question.qtype;

  const updateSettings = changed => {
    onChange({
      qsettings: {
        ...(question.qsettings || {}),
        ...changed
      }
    });
  };

  const addOption = () => {
    const newOption = {
      id: `option-new-${Date.now()}`,
      text: ""
    };

    onChange({
      options: [...(question.options || []), newOption]
    });
  };

  const updateOption = (id, text) => {
    onChange({
      options: (question.options || []).map(o =>
        o.id === id ? { ...o, text } : o
      )
    });
  };

  const removeOption = id => {
    onChange({
      options: (question.options || []).filter(o => o.id !== id)
    });
  };

  const addMatrixRow = () => {
    const index = question.matrix_rows?.length || 0;
    onChange({
      matrix_rows: [
        ...(question.matrix_rows || []),
        {
          id: `matrix-row-new-${Date.now()}`,
          text: `Строка ${index + 1}`,
          value: `row_${index + 1}`
        }
      ]
    });
  };

  const updateMatrixRow = (id, text) => {
    onChange({
      matrix_rows: (question.matrix_rows || []).map(row =>
        row.id === id ? { ...row, text } : row
      )
    });
  };

  const removeMatrixRow = id => {
    onChange({
      matrix_rows: (question.matrix_rows || []).filter(row => row.id !== id)
    });
  };

  const addMatrixColumn = () => {
    const index = question.matrix_columns?.length || 0;
    onChange({
      matrix_columns: [
        ...(question.matrix_columns || []),
        {
          id: `matrix-column-new-${Date.now()}`,
          text: `Вариант ${index + 1}`,
          value: `column_${index + 1}`
        }
      ]
    });
  };

  const updateMatrixColumn = (id, text) => {
    onChange({
      matrix_columns: (question.matrix_columns || []).map(column =>
        column.id === id ? { ...column, text } : column
      )
    });
  };

  const removeMatrixColumn = id => {
    onChange({
      matrix_columns: (question.matrix_columns || []).filter(column => column.id !== id)
    });
  };

  return (
    <Card ref={setNodeRef} style={style} sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
          <IconButton {...listeners} {...attributes}>
            <DragIndicatorIcon />
          </IconButton>

          <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
            {typeLabel}
          </Typography>

          <IconButton color="error" onClick={onDelete}>
            <DeleteIcon />
          </IconButton>
        </Box>

        <TextField
          fullWidth
          label="Текст вопроса"
          value={question.text}
          onChange={e => onChange({ text: e.target.value })}
          sx={{ mb: 2 }}
        />

        <FormControlLabel
          sx={{ mb: 2 }}
          control={
            <Checkbox
              checked={question.required ?? true}
              onChange={e => onChange({ required: e.target.checked })}
            />
          }
          label="Обязательный вопрос"
        />

        {question.qtype === QuestionType.DROPDOWN && (
          <TextField
            fullWidth
            label="Плейсхолдер"
            value={question.qsettings?.placeholder || ""}
            onChange={e => updateSettings({ placeholder: e.target.value })}
            sx={{ mb: 2 }}
          />
        )}

        {optionBasedTypes.includes(question.qtype) && (
          <>
            <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
              <Typography variant="body2" sx={{ flexGrow: 1 }}>
                Варианты ответа
              </Typography>

              <FormControlLabel
                control={
                  <Checkbox
                    checked={question.randomize_options ?? false}
                    onChange={e => onChange({ randomize_options: e.target.checked })}
                  />
                }
                label="Перемешивать"
              />
            </Box>

            {question.options?.map(o => (
              <Box key={o.id} sx={{ display: "flex", mb: 1 }}>
                <TextField
                  fullWidth
                  value={o.text}
                  label="Вариант"
                  onChange={e => updateOption(o.id, e.target.value)}
                />

                <IconButton
                  color="error"
                  onClick={() => removeOption(o.id)}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}

            <Button onClick={addOption}>Добавить вариант</Button>
          </>
        )}

        {question.qtype === QuestionType.YESNO && (
          <Typography variant="body2" color="text.secondary">
            Ответы: Да / Нет
          </Typography>
        )}

        {question.qtype === QuestionType.RANKING && (
          <FormControlLabel
            sx={{ mt: 1, mb: 1 }}
            control={
              <Checkbox
                checked={question.qsettings?.full_ranking ?? true}
                onChange={e => updateSettings({ full_ranking: e.target.checked })}
              />
            }
            label="Требовать ранжирование всех вариантов"
          />
        )}

        {matrixTypes.includes(question.qtype) && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Строки матрицы
            </Typography>

            {(question.matrix_rows || []).map(row => (
              <Box key={row.id} sx={{ display: "flex", mb: 1 }}>
                <TextField
                  fullWidth
                  value={row.text}
                  label="Строка"
                  onChange={e => updateMatrixRow(row.id, e.target.value)}
                />

                <IconButton color="error" onClick={() => removeMatrixRow(row.id)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}

            <Button onClick={addMatrixRow} sx={{ mb: 2 }}>
              Добавить строку
            </Button>

            <Typography variant="body2" sx={{ mb: 1 }}>
              Колонки матрицы
            </Typography>

            {(question.matrix_columns || []).map(column => (
              <Box key={column.id} sx={{ display: "flex", mb: 1 }}>
                <TextField
                  fullWidth
                  value={column.text}
                  label="Колонка"
                  onChange={e => updateMatrixColumn(column.id, e.target.value)}
                />

                <IconButton color="error" onClick={() => removeMatrixColumn(column.id)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}

            <Button onClick={addMatrixColumn}>
              Добавить колонку
            </Button>
          </Box>
        )}

        {question.qtype === QuestionType.SCALE && (
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <TextField
              type="number"
              label="Минимум"
              value={question.qsettings?.min ?? 1}
              onChange={e => updateSettings({ min: Number(e.target.value) })}
            />
            <TextField
              type="number"
              label="Максимум"
              value={question.qsettings?.max ?? 5}
              onChange={e => updateSettings({ max: Number(e.target.value) })}
            />
            <TextField
              type="number"
              label="Шаг"
              value={question.qsettings?.step ?? 1}
              onChange={e => updateSettings({ step: Number(e.target.value) })}
            />
          </Box>
        )}

        {question.qtype === QuestionType.NUMBER && (
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <TextField
              type="number"
              label="Минимум"
              value={question.qsettings?.min ?? ""}
              onChange={e => updateSettings({ min: toNumberOrEmpty(e.target.value) })}
            />
            <TextField
              type="number"
              label="Максимум"
              value={question.qsettings?.max ?? ""}
              onChange={e => updateSettings({ max: toNumberOrEmpty(e.target.value) })}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={question.qsettings?.integer ?? false}
                  onChange={e => updateSettings({ integer: e.target.checked })}
                />
              }
              label="Только целое"
            />
          </Box>
        )}

        {question.qtype === QuestionType.DATE && (
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <TextField
              type="date"
              label="Минимальная дата"
              value={question.qsettings?.min || ""}
              InputLabelProps={{ shrink: true }}
              onChange={e => updateSettings({ min: e.target.value })}
            />
            <TextField
              type="date"
              label="Максимальная дата"
              value={question.qsettings?.max || ""}
              InputLabelProps={{ shrink: true }}
              onChange={e => updateSettings({ max: e.target.value })}
            />
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
