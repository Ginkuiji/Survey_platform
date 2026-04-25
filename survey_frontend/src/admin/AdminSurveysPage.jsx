import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
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

import { fetchAdminSurveys } from "../api/surveys";
import { useNavigate } from "react-router-dom";

export default function AdminSurveysPage() {
  const navigate = useNavigate();

  const [status, setStatus] = useState("");
  const [author, setAuthor] = useState("");
  const [date, setDate] = useState("");

  const { data: surveys } = useQuery({
    queryKey: ["allSurveys"],
    queryFn: fetchAdminSurveys
  });

  if (!surveys) return null;

  const authors = Array.from(new Set(surveys.map(s => s.author)));

  // Фильтрация
  const filtered = surveys.filter(s => {
    const okStatus = status ? s.status === status : true;
    const okAuthor = author ? s.author === author : true;
    const okDate = date ? s.starts_at === date : true;
    return okStatus && okAuthor && okDate;
  });

  return (
    <Container sx={{ mt: 4, width: "125%" }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Опросы
      </Typography>

      {/* Фильтры */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>

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
                  onClick={() => navigate(`/admin/surveys/${s.id}`)}
                >
                  <TableCell>{s.title}</TableCell>
                  <TableCell>{s.description}</TableCell>
                  <TableCell>{s.status}</TableCell>
                  <TableCell>{s.author}</TableCell>
                  <TableCell>{s.responses_count}</TableCell>
                  <TableCell>{s.starts_at}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Container>
  );
}
