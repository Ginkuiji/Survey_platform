import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAdminSurveys } from "../../api/surveys";
import {
  Container,
  Typography,
  Card,
  CardContent,
  TextField,
  Grid,
  Chip
} from "@mui/material";
import { useNavigate } from "react-router-dom";

export default function SurveyAnalyticsListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const { data: surveys } = useQuery({
    queryKey: ["admin-surveys"],
    queryFn: fetchAdminSurveys
  });

  if (!surveys) return null;

  const normalizedSearch = search.trim().toLowerCase();
  const filteredSurveys = surveys.filter(survey => {
    if (survey.status === "deleted") return false;
    return !normalizedSearch
      || survey.title.toLowerCase().includes(normalizedSearch)
      || (survey.description || "").toLowerCase().includes(normalizedSearch);
  });

  return (
    <Container sx={{ mt: 0 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Аналитика моих опросов
      </Typography>

      <TextField
        fullWidth
        label="Поиск по названию и описанию"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        sx={{ mb: 3 }}
      />

      {filteredSurveys.length === 0 && (
        <Typography variant="body1">
          Опросы с доступной аналитикой не найдены.
        </Typography>
      )}

      <Grid container spacing={3}>
        {filteredSurveys.map(survey => (
          <Grid item xs={12} md={6} lg={4} key={survey.id}>
            <Card
              sx={{ cursor: "pointer", width: "100%" }}
              onClick={() => navigate(`/analytics/surveys/${survey.id}`)}
            >
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1 }}>
                  {survey.title}
                </Typography>

                <Typography variant="body2" sx={{ mb: 1 }}>
                  {survey.description}
                </Typography>

                <Typography variant="body2" sx={{ mb: 1 }}>
                  Ответов: <strong>{survey.responses_count}</strong>
                </Typography>

                <Chip
                  label={
                    survey.status === "active"
                      ? "Активен"
                      : survey.status === "draft"
                      ? "Черновик"
                      : "Завершен"
                  }
                  color={
                    survey.status === "active"
                      ? "success"
                      : survey.status === "draft"
                      ? "warning"
                      : "default"
                  }
                  size="small"
                />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}
