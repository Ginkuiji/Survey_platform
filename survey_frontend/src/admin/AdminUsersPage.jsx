import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Container,
  Typography,
  TextField,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Card,
  CardContent
} from "@mui/material";
import { fetchAllUsers } from "../api/users";
import { useNavigate } from "react-router-dom";

export default function AdminUsersPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const { data: users } = useQuery({
    queryKey: ["allUsers"],
    queryFn: fetchAllUsers
  });

  if (!users) return null;

  // Фильтрация по email, имени, роли
  const filtered = users.filter(u => {
    const term = search.toLowerCase();
    return (
      u.email.toLowerCase().includes(term) ||
      u.first_name.toLowerCase().includes(term) ||
      u.last_name.toLowerCase().includes(term) ||
      u.role.toLowerCase().includes(term)
    );
  });

  return (
    <Container maxWidth={false} sx={{ mt: "-25%", width: "170%" }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Пользователи
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <TextField
            label="Поиск по имени, email или роли"
            fullWidth
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell>Имя</TableCell>
                <TableCell>Роль</TableCell>
                <TableCell>Дата регистрации</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {filtered.map(user => (
                <TableRow
                  key={user.id}
                  hover
                  sx={{ cursor: "pointer" }}
                  onClick={() => navigate(`/admin/users/${user.id}`)}
                >
                  <TableCell>{user.email}</TableCell>
                  <TableCell>{user.first_name} {user.last_name}</TableCell>
                  <TableCell>{user.role}</TableCell>
                  <TableCell>{user.date_joined}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Container>
  );
}