import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSurveys } from "../api/surveys";
import { fetchUserProfile } from "../api/users";
import {
  Card,
  CardContent,
  Typography,
  Container,
  Box,
  Chip,
  TextField,
  MenuItem
} from "@mui/material";
import { Link } from "react-router-dom";

export default function SurveyListPage() {
  const { data: surveys } = useQuery({
    queryKey: ["surveys"],
    queryFn: fetchSurveys
  });

  const { data: user } = useQuery({
    queryKey: ["userProfile"],
    queryFn: fetchUserProfile
  });

  // --- Фильтры ---
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  if (!surveys || !user) return null;

  // --- Ссылка в зависимости от роли ---
  const getSurveyLink = (survey) => {
    return user.role == "admin" || user.role == "organizer"
      ? `/surveys/${survey.id}`
      : `/surveys/${survey.id}`;
  };

  // --- Фильтрация ---
  const filtered = surveys.filter((s) => {
    const matchesSearch =
      s.title.toLowerCase().includes(search.toLowerCase()) ||
      (s.description ?? "").toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ? true : s.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <Container maxWidth="lg" sx={{ mt: 3, width: "200%" }}>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Список опросов
      </Typography>

      {/* --- Панель фильтрации --- */}
      <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
        <TextField
          label="Поиск"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ width: 260 }}
        />

        <TextField
          select
          label="Статус"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          sx={{ width: 200 }}
        >
          <MenuItem value="all">Все</MenuItem>
          <MenuItem value="active">Активные</MenuItem>
          <MenuItem value="draft">Черновики</MenuItem>
          <MenuItem value="closed">Завершённые</MenuItem>
        </TextField>
      </Box>

      {/* --- Список опросов --- */}
      {filtered.map((s) => (
        <Link
          key={s.id}
          to={getSurveyLink(s)}
          style={{ textDecoration: "none" }}
        >
          <Card sx={{ mb: 2, cursor: "pointer" }}>
            <CardContent
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start"
              }}
            >
              {/* Левая часть */}
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6">{s.title}</Typography>

                <Typography variant="body2" sx={{ mb: 1 }}>
                  {s.description || "Без описания"}
                </Typography>

                {/* Статус */}
                <Chip
                  label={
                    s.status === "active"
                      ? "Активен"
                      : s.status === "draft"
                      ? "Черновик"
                      : "Завершён"
                  }
                  size="small"
                  sx={{
                    backgroundColor:
                      s.status === "active"
                        ? "#C8E6C9"
                        : s.status === "draft"
                        ? "#FFF3CD"
                        : "#E0E0E0",
                    color:
                      s.status === "active"
                        ? "#256029"
                        : s.status === "draft"
                        ? "#705c00"
                        : "#424242"
                  }}
                />
              </Box>

              {/* Правая часть: даты */}
              <Box sx={{ textAlign: "right", minWidth: 140 }}>
                <Typography variant="caption" sx={{ color: "gray", display: "block" }}>
                  Начало: {s.starts_at || "—"}
                </Typography>

                <Typography variant="caption" sx={{ color: "gray", display: "block" }}>
                  Конец: {s.ends_at || "—"}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Link>
      ))}

      {filtered.length === 0 && (
        <Typography variant="body2" sx={{ color: "gray", mt: 3 }}>
          Опросы не найдены
        </Typography>
      )}
    </Container>
  );
}
