import { Grid, Card, CardContent, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboardData } from "../../api/dashboard";

export default function AdminStatsTop() {
  // Мок-данные (позже заменим на API)
  const { data } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: fetchDashboardData,
  });

  if (!data) return null;

  const stats = data.stats;

  const items = [
    { label: "Всего пользователей", value: stats.totalUsers },
    { label: "Активных пользователей", value: stats.activeUsers },
    { label: "Всего опросов", value: stats.totalSurveys },
    { label: "Активных опросов", value: stats.activeSurveys },
    { label: "Ответов сегодня", value: stats.todaysResponses }
  ];

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {items.map((item, idx) => (
        <Grid item xs={12} sm={6} md={4} lg={3} key={idx}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6">{item.label}</Typography>
              <Typography variant="h4" sx={{ mt: 1, fontWeight: "bold" }}>
                {item.value}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
