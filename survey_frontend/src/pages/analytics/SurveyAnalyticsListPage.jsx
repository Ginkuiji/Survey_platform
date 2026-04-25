import { useQuery } from "@tanstack/react-query";
import { fetchAdminSurveys } from "../../api/surveys";
import {
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip
} from "@mui/material";
import { useNavigate } from "react-router-dom";

export default function SurveyAnalyticsListPage() {
  const navigate = useNavigate();

  const { data: surveys } = useQuery({
    queryKey: ["admin-surveys"],
    queryFn: fetchAdminSurveys
  });

  if (!surveys) return null;

  return (
    <Container sx={{ mt: "-15%" }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Аналитика моих опросов
      </Typography>

      {surveys.length === 0 && (
        <Typography variant="body1">
          У вас пока нет опросов с доступной аналитикой.
        </Typography>
      )}

      <Grid container spacing={3}>
        {surveys.map(survey => (
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
