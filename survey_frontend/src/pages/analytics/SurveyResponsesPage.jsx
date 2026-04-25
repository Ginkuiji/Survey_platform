import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  Modal,
  Pagination,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { fetchSurveyById, fetchSurveyResponses } from "../../api/surveys";

const modalStyle = {
  position: "absolute",
  top: "50%",
  left: "50%",
  transform: "translate(-50%, -50%)",
  width: "60%",
  bgcolor: "background.paper",
  boxShadow: 24,
  p: 4,
  borderRadius: 2,
};

function formatAnswerValue(answer) {
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
  return "";
}

function getAllSurveyQuestions(survey) {
  return [
    ...(survey.questions || []),
    ...((survey.pages || []).flatMap(page => page.questions || [])),
  ];
}

function getQuestionText(allQuestions, questionId) {
  return allQuestions.find(question => question.id === questionId)?.text || `Вопрос #${questionId}`;
}

function getFinishTypeLabel(response) {
  return response.screened_out ? "Screened out" : "Завершён";
}

export default function SurveyResponsesPage() {
  const { id } = useParams();

  const { data: survey } = useQuery({
    queryKey: ["survey", id],
    queryFn: () => fetchSurveyById(id),
  });

  const { data: responses } = useQuery({
    queryKey: ["survey-responses", id],
    queryFn: () => fetchSurveyResponses(id),
  });

  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState(null);

  if (!survey || !responses) return null;

  const allQuestions = getAllSurveyQuestions(survey);
  const rowsPerPage = 5;

  const filtered = responses.filter(response => {
    const userLabel = response.user?.email || "Аноним";
    const byUser = !search || userLabel.toLowerCase().includes(search.toLowerCase());
    const finished = response.finished_at ? new Date(response.finished_at) : null;
    const byDate =
      (!dateFrom || (finished && finished >= new Date(dateFrom))) &&
      (!dateTo || (finished && finished <= new Date(dateTo)));

    return byUser && byDate;
  });

  const totalPages = Math.max(Math.ceil(filtered.length / rowsPerPage), 1);
  const paginated = filtered.slice((page - 1) * rowsPerPage, page * rowsPerPage);

  const exportCSV = () => {
    let csv = "response_id,user,finish_type,finished_at,screened_out_reason,question,answer\n";

    responses.forEach(response => {
      response.answers.forEach(answer => {
        const qtext = getQuestionText(allQuestions, answer.question);
        const value = formatAnswerValue(answer);
        csv += `${response.id},"${response.user?.email || "Аноним"}","${getFinishTypeLabel(response)}","${response.finished_at || ""}","${response.screened_out_reason || ""}","${qtext}","${value}"\n`;
      });
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `survey_${id}_responses.csv`;
    link.click();
  };

  return (
    <Container maxWidth={false} sx={{ mt: 4, width: "150%" }}>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Ответы по опросу: {survey.title}
      </Typography>

      <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
        <TextField
          label="Поиск по пользователю"
          value={search}
          onChange={event => setSearch(event.target.value)}
          sx={{ width: "40%" }}
        />

        <TextField
          type="date"
          label="С даты"
          InputLabelProps={{ shrink: true }}
          value={dateFrom}
          onChange={event => setDateFrom(event.target.value)}
        />

        <TextField
          type="date"
          label="По дату"
          InputLabelProps={{ shrink: true }}
          value={dateTo}
          onChange={event => setDateTo(event.target.value)}
        />
      </Box>

      <Card>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Пользователь</TableCell>
                <TableCell>Тип завершения</TableCell>
                <TableCell>Причина скрининга</TableCell>
                <TableCell>Завершено</TableCell>
                <TableCell>Ответы</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {paginated.map(response => (
                <TableRow
                  key={response.id}
                  hover
                  sx={{ cursor: "pointer" }}
                  onClick={() => {
                    setSelected(response);
                    setModalOpen(true);
                  }}
                >
                  <TableCell>{response.id}</TableCell>
                  <TableCell>{response.user?.email || "Аноним"}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={response.screened_out ? "warning" : "success"}
                      label={getFinishTypeLabel(response)}
                    />
                  </TableCell>
                  <TableCell>{response.screened_out_reason || "—"}</TableCell>
                  <TableCell>
                    {response.finished_at ? new Date(response.finished_at).toLocaleString() : "—"}
                  </TableCell>
                  <TableCell>
                    {response.answers.slice(0, 2).map(answer => (
                      <div key={answer.id}>
                        {getQuestionText(allQuestions, answer.question)}: {formatAnswerValue(answer)}
                      </div>
                    ))}
                    {response.answers.length > 2 && <i>…ещё</i>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
            <Pagination count={totalPages} page={page} onChange={(_, nextPage) => setPage(nextPage)} />
          </Box>
        </CardContent>
      </Card>

      <Box sx={{ mt: 4 }}>
        <Button variant="outlined" onClick={exportCSV}>
          Экспорт CSV
        </Button>
      </Box>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)}>
        <Box sx={modalStyle}>
          {selected && (
            <>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Ответ #{selected.id}
              </Typography>

              <Typography sx={{ mb: 1 }}>
                Пользователь: <strong>{selected.user?.email || "Аноним"}</strong>
              </Typography>

              <Typography sx={{ mb: 1 }}>
                Тип завершения: <strong>{getFinishTypeLabel(selected)}</strong>
              </Typography>

              {selected.complete_reason && (
                <Typography sx={{ mb: 1 }}>
                  Complete reason: <strong>{selected.complete_reason}</strong>
                </Typography>
              )}

              {selected.screened_out && (
                <>
                  <Typography sx={{ mb: 1 }}>
                    Причина скрининга: <strong>{selected.screened_out_reason || "Без указания причины"}</strong>
                  </Typography>
                  <Typography sx={{ mb: 1 }}>
                    Screened out at:{" "}
                    <strong>{selected.screened_out_at ? new Date(selected.screened_out_at).toLocaleString() : "—"}</strong>
                  </Typography>
                </>
              )}

              <Typography sx={{ mb: 2 }}>
                Завершено: <strong>{selected.finished_at ? new Date(selected.finished_at).toLocaleString() : "—"}</strong>
              </Typography>

              <Divider sx={{ mb: 2 }} />

              {selected.answers.map(answer => (
                <Box key={answer.id} sx={{ mb: 2 }}>
                  <strong>{getQuestionText(allQuestions, answer.question)}</strong>
                  <br />
                  {formatAnswerValue(answer)}
                </Box>
              ))}
            </>
          )}
        </Box>
      </Modal>
    </Container>
  );
}
