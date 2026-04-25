import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow
} from "@mui/material";

import { useQuery } from "@tanstack/react-query";
import { fetchDashboardData } from "../../api/dashboard";

export default function AdminRecentSurveys() {

  const { data } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: fetchDashboardData
  });

  if (!data) return null;

  // Позже: сортировка по created_at из API.
  // Сейчас: просто берём последние 5
  const lastSurveys = data.recentSurveys;

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Последние созданные опросы
        </Typography>

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Название</TableCell>
              <TableCell>Описание</TableCell>
              <TableCell>Количество вопросов</TableCell>
              <TableCell>Дата создания</TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {lastSurveys.map(s => (
              <TableRow key={s.id}>
                <TableCell>{s.title}</TableCell>
                <TableCell>{s.description}</TableCell>
                <TableCell>{s.questions_count ?? 0}</TableCell>
                <TableCell>{s.created_at}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
