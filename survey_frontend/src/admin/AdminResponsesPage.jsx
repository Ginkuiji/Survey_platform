import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import {
  fetchAdminSurveyById,
  fetchSurveyResponses,
  updateSurveyResponseStatus,
} from "../api/surveys";

function formatDate(value) {
  if (!value) return "Не указана";
  return new Date(value).toLocaleString("ru-RU");
}

function responseEmail(response) {
  return response.user?.email || "Аноним";
}

function getCompletionType(response) {
  if (!response.is_complete) {
    return { label: "-", color: "default" };
  }

  if (response.screened_out || response.complete_reason === "screened_out") {
    return { label: "Отсечен", color: "warning" };
  }

  return { label: "Полностью", color: "success" };
}

export default function AdminResponsesPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: survey } = useQuery({
    queryKey: ["admin-survey", id],
    queryFn: () => fetchAdminSurveyById(id),
  });

  const { data: responses } = useQuery({
    queryKey: ["survey-responses", id],
    queryFn: () => fetchSurveyResponses(id),
  });

  const statusMutation = useMutation({
    mutationFn: ({ responseId, status }) =>
      updateSurveyResponseStatus(id, responseId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["survey-responses", id] });
    },
  });

  const responseStats = useMemo(
    () =>
      responses?.reduce(
        (stats, response) => {
          if (!response.is_complete) {
            return stats;
          }

          stats.completedTotal += 1;

          if (response.screened_out || response.complete_reason === "screened_out") {
            stats.screenedOut += 1;
          } else {
            stats.completedFully += 1;
          }

          return stats;
        },
        { completedFully: 0, screenedOut: 0, completedTotal: 0 }
      ) || { completedFully: 0, screenedOut: 0, completedTotal: 0 },
    [responses]
  );

  if (!survey || !responses) return null;

  const toggleStatus = (event, response) => {
    event.stopPropagation();
    const nextStatus = response.status === "blocked" ? "active" : "blocked";
    statusMutation.mutate({ responseId: response.id, status: nextStatus });
  };

  return (
    <Container maxWidth={false} sx={{ mt: 4, width: "100%" }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Ответы на опрос: {survey.title}
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {survey.description}
      </Typography>

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="body2">
              Всего ответов
            </Typography>
            <Typography variant="h5">{responses.length}</Typography>
          </CardContent>
        </Card>

        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="body2">
              Полностью пройденных
            </Typography>
            <Typography variant="h5">{responseStats.completedFully}</Typography>
          </CardContent>
        </Card>

        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="body2">
              Отсеченных
            </Typography>
            <Typography variant="h5">{responseStats.screenedOut}</Typography>
          </CardContent>
        </Card>

        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="body2">
              Завершенных всего
            </Typography>
            <Typography variant="h5">{responseStats.completedTotal}</Typography>
          </CardContent>
        </Card>

        <Card sx={{ flex: 2 }}>
          <CardContent>
            <Typography color="text.secondary" variant="body2">
              Даты проведения
            </Typography>
            <Typography variant="body1">
              {formatDate(survey.starts_at)} - {formatDate(survey.ends_at)}
            </Typography>
          </CardContent>
        </Card>
      </Stack>

      <Card>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Почта респондента</TableCell>
                <TableCell>Дата ответа</TableCell>
                <TableCell>Завершённость</TableCell>
                <TableCell>Тип завершения</TableCell>
                <TableCell>Активность</TableCell>
                <TableCell align="right">Действия</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {responses.map(response => {
                const completionType = getCompletionType(response);

                return (
                  <TableRow
                    key={response.id}
                    hover
                    sx={{ cursor: "pointer" }}
                    onClick={() =>
                      navigate(`/analytics/surveys/${id}/responses/${response.id}`)
                    }
                  >
                    <TableCell>{response.id}</TableCell>
                    <TableCell>{responseEmail(response)}</TableCell>
                    <TableCell>
                      {formatDate(response.finished_at || response.started_at)}
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={response.is_complete ? "success" : "warning"}
                        label={response.is_complete ? "Завершён" : "Не завершён"}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={completionType.color}
                        label={completionType.label}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={response.status === "blocked" ? "error" : "primary"}
                        label={response.status === "blocked" ? "Заблокирован" : "Активен"}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        variant="outlined"
                        size="small"
                        disabled={statusMutation.isPending}
                        onClick={event => toggleStatus(event, response)}
                      >
                        {response.status === "blocked" ? "Разблокировать" : "Заблокировать"}
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}

              {!responses.length && (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Box sx={{ py: 4, textAlign: "center" }}>
                      <Typography color="text.secondary">
                        По этому опросу пока нет ответов.
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Container>
  );
}
