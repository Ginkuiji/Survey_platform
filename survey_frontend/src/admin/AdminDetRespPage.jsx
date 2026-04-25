import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  Stack,
  Typography,
} from "@mui/material";

import { fetchAdminSurveyById, fetchSurveyResponseById } from "../api/surveys";

function formatDate(value) {
  if (!value) return "Не указана";
  return new Date(value).toLocaleString("ru-RU");
}

function getAnswerValue(answer) {
  if (answer.selected_options?.length) {
    return answer.selected_options.map(option => option.text).join(", ");
  }

  if (answer.matrix_cells?.length) {
    return answer.matrix_cells
      .map(cell => `${cell.row_text}: ${cell.column_text}`)
      .join("; ");
  }

  if (answer.ranking_items?.length) {
    return [...answer.ranking_items]
      .sort((a, b) => a.rank - b.rank)
      .map(item => `${item.rank}. ${item.option_text}`)
      .join("; ");
  }

  if (answer.text) return answer.text;
  if (answer.num !== null && answer.num !== undefined) return answer.num;
  return "Нет ответа";
}

function getAllSurveyQuestions(survey) {
  return [
    ...(survey.questions || []),
    ...((survey.pages || []).flatMap(page => page.questions || [])),
  ];
}

export default function AdminDetRespPage() {
  const { id, responseId } = useParams();

  const { data: survey } = useQuery({
    queryKey: ["admin-survey", id],
    queryFn: () => fetchAdminSurveyById(id),
  });

  const { data: response } = useQuery({
    queryKey: ["survey-response", id, responseId],
    queryFn: () => fetchSurveyResponseById(id, responseId),
  });

  if (!survey || !response) return null;

  const respondent = response.user?.email || "Аноним";
  const allQuestions = getAllSurveyQuestions(survey);

  return (
    <Container maxWidth={false} sx={{ mt: 4, width: "100%" }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Анкета респондента
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {survey.title}
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <Box sx={{ flex: 1 }}>
              <Typography color="text.secondary" variant="body2">
                Респондент
              </Typography>
              <Typography variant="h6">{respondent}</Typography>
            </Box>

            <Box sx={{ flex: 1 }}>
              <Typography color="text.secondary" variant="body2">
                Начало
              </Typography>
              <Typography>{formatDate(response.started_at)}</Typography>
            </Box>

            <Box sx={{ flex: 1 }}>
              <Typography color="text.secondary" variant="body2">
                Завершение
              </Typography>
              <Typography>{formatDate(response.finished_at)}</Typography>
            </Box>

            <Box sx={{ flex: 1 }}>
              <Typography color="text.secondary" variant="body2">
                Статусы
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap" }} useFlexGap>
                <Chip
                  size="small"
                  color={response.is_complete ? "success" : "warning"}
                  label={response.is_complete ? "Завершён" : "Не завершён"}
                />
                <Chip
                  size="small"
                  color={response.status === "blocked" ? "error" : "primary"}
                  label={response.status === "blocked" ? "Заблокирован" : "Активен"}
                />
                {response.screened_out && (
                  <Chip size="small" color="warning" label="Screened out" />
                )}
              </Stack>
            </Box>
          </Stack>

          {response.screened_out && (
            <Box sx={{ mt: 2 }}>
              <Typography color="text.secondary" variant="body2">
                Причина скрининга
              </Typography>
              <Typography>{response.screened_out_reason || "Без указания причины"}</Typography>

              <Typography color="text.secondary" variant="body2" sx={{ mt: 1 }}>
                Время скрининга
              </Typography>
              <Typography>{formatDate(response.screened_out_at)}</Typography>
            </Box>
          )}

          {response.complete_reason && (
            <Box sx={{ mt: 2 }}>
              <Typography color="text.secondary" variant="body2">
                Complete reason
              </Typography>
              <Typography>{response.complete_reason}</Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      <Typography variant="h5" sx={{ mb: 2 }}>
        Ответы
      </Typography>

      {allQuestions.map((question, index) => {
        const answer = response.answers.find(item => item.question === question.id);

        return (
          <Card key={question.id} sx={{ mb: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
                Вопрос {index + 1}
              </Typography>
              <Typography variant="h6" sx={{ mb: 1 }}>
                {question.text}
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography>{answer ? getAnswerValue(answer) : "Нет ответа"}</Typography>
            </CardContent>
          </Card>
        );
      })}
    </Container>
  );
}
