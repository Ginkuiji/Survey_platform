import { Container, Typography } from "@mui/material";
import AdminStatsTop from "./components/AdminStatsTop";
import AdminCharts from "./components/AdminCharts";
import AdminRecentUsers from "./components/AdminRecentUsers";
import AdminRecentSurveys from "./components/AdminRecentSurveys";

export default function AdminDashboardPage() {
  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Панель администратора
      </Typography>

      {/* Верхний блок — KPI карточки */}
      <AdminStatsTop />
      <AdminRecentUsers />
      <AdminRecentSurveys />
      <AdminCharts />
      {/* Здесь позже появятся:
          <AdminShortcuts/>
       */}
    </Container>
  );
}
