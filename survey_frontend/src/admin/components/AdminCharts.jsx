import { Card, CardContent, Typography, Grid, Box } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, Tooltip, PieChart, Pie, Cell, BarChart, Bar, CartesianGrid, Legend, ResponsiveContainer } from "recharts";
import { fetchDashboardData } from "../../api/dashboard";

export default function AdminCharts() {

  const { data } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: fetchDashboardData
  });

  // 2. Статусы опросов
  const { responsesByDay, surveyStatusData, registrations } = data?.charts || {
    responsesByDay: [],
    surveyStatusData: [],
    registrations: [],
  };

  // 3. Регистрации пользователей
  

  // Если данные еще не загружены
  if (!data) return null;

  const COLORS = ["#4CAF50", "#FFA726", "#29B6F6"];

  return (
    <Grid container spacing={3} sx={{ mt: 2, mb: 3 }}>

      {/* График 1 */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Количество завершённых ответов по дням
            </Typography>
            <LineChart width={400} height={250} data={responsesByDay}>
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#3f51b5" strokeWidth={2} />
            </LineChart>
          </CardContent>
        </Card>
      </Grid>

      {/* График 2 */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Статусы опросов
            </Typography>
            <PieChart width={400} height={250}>
              <Pie
                data={surveyStatusData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label
              >
                {surveyStatusData.map((entry, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </CardContent>
        </Card>
      </Grid>

      {/* График 3 */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Регистрации пользователей по дням
            </Typography>
            <BarChart width={800} height={300} data={registrations}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="users" fill="#82ca9d" />
            </BarChart>
          </CardContent>
        </Card>
      </Grid>

    </Grid>
  );
}
