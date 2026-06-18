import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Container,
  Typography,
  Card,
  CardContent,
  Table,
  TableHead,
  TableCell,
  TableRow,
  TableBody,
  TextField,
  MenuItem,
  Grid
} from "@mui/material";

import { fetchAdminSurveys, updateSurvey } from "../api/surveys";
import { useNavigate } from "react-router-dom";

const STATUS_LABELS = {
  draft: "Черновик",
  active: "Активный",
  closed: "Закрыт",
  deleted: "Удалён",
};

export default function AdminSurveysPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [author, setAuthor] = useState("");
  const [date, setDate] = useState("");
  const [statusError, setStatusError] = useState("");

  const { data: surveys } = useQuery({
    queryKey: ["allSurveys"],
    queryFn: fetchAdminSurveys
  });

  const statusMutation = useMutation({
    mutationFn: ({ surveyId, nextStatus }) =>
      updateSurvey(surveyId, { status: nextStatus }),
    onSuccess: () => {
      setStatusError("");
      queryClient.invalidateQueries({ queryKey: ["allSurveys"] });
      queryClient.invalidateQueries({ queryKey: ["admin-surveys"] });
      queryClient.invalidateQueries({ queryKey: ["surveys"] });
    },
    onError: (error) => {
      setStatusError(error.message || "Не удалось изменить статус опроса.");
    },
  });

  if (!surveys) return null;

  const authors = Array.from(new Set(surveys.map(s => s.author)));

  // Фильтрация
  const filtered = surveys.filter(s => {
    const normalizedSearch = search.trim().toLowerCase();
    const okSearch = !normalizedSearch
      || s.title.toLowerCase().includes(normalizedSearch)
      || (s.description || "").toLowerCase().includes(normalizedSearch);
    const okStatus = status ? s.status === status : true;
    const okAuthor = author ? s.author === author : true;
    const okDate = date ? s.starts_at === date : true;
    return okSearch && okStatus && okAuthor && okDate;
  });

  return (
    <Container sx={{ mt: 4, width: "125%" }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Опросы
      </Typography>

      {statusError && <Alert severity="error" sx={{ mb: 2 }}>{statusError}</Alert>}

      {/* Фильтры */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4} sx={{ width: "30%" }}>
              <TextField
                label="Поиск по названию и описанию"
                fullWidth
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={4} sx={{width: "20%"}}>
              <TextField
                label="Статус"
                select
                fullWidth
                value={status}
                onChange={e => setStatus(e.target.value)}
              >
                <MenuItem value="">Все</MenuItem>
                <MenuItem value="draft">Черновик</MenuItem>
                <MenuItem value="active">Активный</MenuItem>
                <MenuItem value="closed">Закрыт</MenuItem>
                <MenuItem value="deleted">Удалён</MenuItem>
              </TextField>
            </Grid>

            <Grid item xs={12} md={4} sx={{width: "20%"}}>
              <TextField
                label="Автор"
                select
                fullWidth
                value={author}
                onChange={e => setAuthor(e.target.value)}
              >
                <MenuItem value="">Все</MenuItem>
                {authors.map(a => (
                  <MenuItem key={a} value={a}>
                    {a}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={12} md={4} sx={{width: "20%"}}>
              <TextField
                label="Дата начала"
                type="date"
                fullWidth
                value={date}
                onChange={e => setDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

          </Grid>
        </CardContent>
      </Card>

      {/* Таблица */}
      <Card>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Название</TableCell>
                <TableCell>Описание</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Автор</TableCell>
                <TableCell>Ответов</TableCell>
                <TableCell>Дата начала</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {filtered.map(s => (
                <TableRow
                  key={s.id}
                  hover
                  sx={{ cursor: "pointer" }}
                  onClick={() => navigate(`/management/surveys/${s.id}`)}
                >
                  <TableCell>{s.title}</TableCell>
                  <TableCell>{s.description}</TableCell>
                  <TableCell onClick={event => event.stopPropagation()}>
                    <TextField
                      select
                      size="small"
                      value={s.status}
                      disabled={statusMutation.isPending}
                      onChange={event => {
                        statusMutation.mutate({
                          surveyId: s.id,
                          nextStatus: event.target.value,
                        });
                      }}
                      sx={{ minWidth: 130 }}
                    >
                      {Object.entries(STATUS_LABELS).map(([value, label]) => (
                        <MenuItem key={value} value={value}>
                          {label}
                        </MenuItem>
                      ))}
                    </TextField>
                  </TableCell>
                  <TableCell>{s.author}</TableCell>
                  <TableCell>{s.responses_count}</TableCell>
                  <TableCell>{s.starts_at}</TableCell>
                </TableRow>
              ))}

              {!filtered.length && (
                <TableRow>
                  <TableCell colSpan={6}>
                    Опросы не найдены.
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
