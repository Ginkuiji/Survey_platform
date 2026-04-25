import {
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Divider,
  FormControlLabel,
  MenuItem,
  TextField,
  Typography,
  IconButton,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  CONDITION_ACTIONS,
  CONDITION_OPERATORS,
  createEmptyCondition,
  getSurveyPages,
  getSurveyQuestions,
} from "../utils/branching";

const optionOperators = ["equals", "not_equals", "contains_option"];
const numericOperators = ["gt", "lt", "gte", "lte"];
const noValueOperators = ["is_answered", "not_answered"];
const choiceTypes = ["single", "multi", "dropdown", "yesno", "ranking"];
const numericTypes = ["scale", "number"];

function getValueMode(condition, sourceQuestion) {
  if (!sourceQuestion || noValueOperators.includes(condition.operator)) return "none";
  if (numericOperators.includes(condition.operator)) return "number";
  if (optionOperators.includes(condition.operator) && choiceTypes.includes(sourceQuestion.qtype)) {
    return "option";
  }
  if (numericTypes.includes(sourceQuestion.qtype)) return "number";
  return "text";
}

export default function BranchingConditionsEditor({
  pages,
  conditions,
  onChange,
  disabled = false,
}) {
  const questions = getSurveyQuestions(pages);
  const pageList = getSurveyPages(pages);
  const questionsById = Object.fromEntries(questions.map(question => [question.id, question]));

  const updateCondition = (conditionId, changed) => {
    onChange(
      conditions.map(condition =>
        condition.id === conditionId ? { ...condition, ...changed } : condition
      )
    );
  };

  const addCondition = () => {
    onChange([...conditions, createEmptyCondition(conditions.length)]);
  };

  const removeCondition = conditionId => {
    onChange(conditions.filter(condition => condition.id !== conditionId));
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            Ветвление и скрининг
          </Typography>
          <Button variant="outlined" onClick={addCondition} disabled={disabled || questions.length === 0}>
            Добавить условие
          </Button>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Условия сохраняются после сохранения структуры опроса. Для новых вопросов варианты будут привязаны после создания ID на сервере.
        </Typography>

        {conditions.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            Условия пока не заданы.
          </Typography>
        )}

        {conditions.map((condition, index) => {
          const sourceQuestion = questionsById[condition.source_question];
          const valueMode = getValueMode(condition, sourceQuestion);

          return (
            <Box key={condition.id} sx={{ py: 2 }}>
              {index > 0 && <Divider sx={{ mb: 2 }} />}

              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                  Условие {index + 1}
                </Typography>
                <IconButton color="error" onClick={() => removeCondition(condition.id)} disabled={disabled}>
                  <DeleteIcon />
                </IconButton>
              </Box>

              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2 }}>
                <TextField
                  select
                  label="Если вопрос"
                  value={condition.source_question || ""}
                  onChange={e => updateCondition(condition.id, {
                    source_question: e.target.value,
                    option: "",
                  })}
                  disabled={disabled}
                >
                  {questions.map(question => (
                    <MenuItem key={question.id} value={question.id}>
                      {question.text || `Вопрос ${question.questionIndex + 1}`}
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  select
                  label="Оператор"
                  value={condition.operator}
                  onChange={e => updateCondition(condition.id, {
                    operator: e.target.value,
                    option: "",
                    value_text: "",
                    value_number: "",
                  })}
                  disabled={disabled}
                >
                  {CONDITION_OPERATORS.map(operator => (
                    <MenuItem key={operator.value} value={operator.value}>
                      {operator.label}
                    </MenuItem>
                  ))}
                </TextField>

                {valueMode === "option" && (
                  <TextField
                    select
                    label="Вариант"
                    value={condition.option || ""}
                    onChange={e => updateCondition(condition.id, { option: e.target.value })}
                    disabled={disabled || !sourceQuestion}
                  >
                    {(sourceQuestion?.options || []).map(option => (
                      <MenuItem key={option.id} value={option.id}>
                        {option.text}
                      </MenuItem>
                    ))}
                  </TextField>
                )}

                {valueMode === "number" && (
                  <TextField
                    type="number"
                    label="Число"
                    value={condition.value_number ?? ""}
                    onChange={e => updateCondition(condition.id, { value_number: e.target.value })}
                    disabled={disabled}
                  />
                )}

                {valueMode === "text" && (
                  <TextField
                    label="Текст/дата"
                    value={condition.value_text || ""}
                    onChange={e => updateCondition(condition.id, { value_text: e.target.value })}
                    disabled={disabled}
                  />
                )}

                <TextField
                  select
                  label="Действие"
                  value={condition.action}
                  onChange={e => updateCondition(condition.id, {
                    action: e.target.value,
                    question: "",
                    page: "",
                    target_page: "",
                  })}
                  disabled={disabled}
                >
                  {CONDITION_ACTIONS.map(action => (
                    <MenuItem key={action.value} value={action.value}>
                      {action.label}
                    </MenuItem>
                  ))}
                </TextField>

                {condition.action === "show_question" && (
                  <TextField
                    select
                    label="Показать вопрос"
                    value={condition.question || ""}
                    onChange={e => updateCondition(condition.id, { question: e.target.value })}
                    disabled={disabled}
                  >
                    {questions.map(question => (
                      <MenuItem key={question.id} value={question.id}>
                        {question.text || `Вопрос ${question.questionIndex + 1}`}
                      </MenuItem>
                    ))}
                  </TextField>
                )}

                {condition.action === "show_page" && (
                  <TextField
                    select
                    label="Показать страницу"
                    value={condition.page || ""}
                    onChange={e => updateCondition(condition.id, { page: e.target.value })}
                    disabled={disabled}
                  >
                    {pageList.map(page => (
                      <MenuItem key={page.id} value={page.id}>
                        {page.title || `Страница ${page.pageIndex + 1}`}
                      </MenuItem>
                    ))}
                  </TextField>
                )}

                {condition.action === "jump_to_page" && (
                  <TextField
                    select
                    label="Перейти на страницу"
                    value={condition.target_page || ""}
                    onChange={e => updateCondition(condition.id, { target_page: e.target.value })}
                    disabled={disabled}
                  >
                    {pageList.map(page => (
                      <MenuItem key={page.id} value={page.id}>
                        {page.title || `Страница ${page.pageIndex + 1}`}
                      </MenuItem>
                    ))}
                  </TextField>
                )}

                {condition.action === "terminate" && (
                  <TextField
                    label="Сообщение скрининга"
                    value={condition.terminate_message || ""}
                    onChange={e => updateCondition(condition.id, { terminate_message: e.target.value })}
                    disabled={disabled}
                  />
                )}

                <TextField
                  label="Ключ группы"
                  value={condition.group_key || ""}
                  onChange={e => updateCondition(condition.id, { group_key: e.target.value })}
                  disabled={disabled}
                />

                <TextField
                  select
                  label="Логика группы"
                  value={condition.group_logic || "all"}
                  onChange={e => updateCondition(condition.id, { group_logic: e.target.value })}
                  disabled={disabled}
                >
                  <MenuItem value="all">Все условия</MenuItem>
                  <MenuItem value="any">Любое условие</MenuItem>
                </TextField>

                <TextField
                  type="number"
                  label="Приоритет"
                  value={condition.priority ?? index}
                  onChange={e => updateCondition(condition.id, { priority: Number(e.target.value) })}
                  disabled={disabled}
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={condition.is_active ?? true}
                      onChange={e => updateCondition(condition.id, { is_active: e.target.checked })}
                      disabled={disabled}
                    />
                  }
                  label="Активно"
                />
              </Box>
            </Box>
          );
        })}
      </CardContent>
    </Card>
  );
}
