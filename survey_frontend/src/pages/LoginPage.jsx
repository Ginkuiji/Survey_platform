import { Container, TextField, Button, Typography, Box } from "@mui/material";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async () => {
    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/token/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
          username,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.email?.[0] || "Ошибка входа");
      }

      localStorage.setItem("accessToken", data.access);
      localStorage.setItem("refreshToken", data.refresh);

      const meRes = await fetch("http://127.0.0.1:8000/api/users/me/", {
        headers: {
          Authorization: `Bearer ${data.access}`,
        },
      });

      const meData = await meRes.json();

      if (!meRes.ok) {
        throw new Error(meData.detail || "Не удалось получить профиль");
      }

      localStorage.setItem("currentUser", JSON.stringify(meData));

      if (meData.role === "admin") {
        navigate("/admin/dashboard");
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err.message || "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container sx={{ mt: 6, display: "flex", flexDirection: "column", alignItems: "center" }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Вход
      </Typography>

      <Box sx={{ width: "100%", maxWidth: "400px" }}>
        <TextField
          label="Email"
          type="email"
          fullWidth
          sx={{ mb: 2 }}
          value={email}
          onChange={e => setEmail(e.target.value)}
        />

        <TextField
          label="Логин"
          type="username"
          fullWidth
          sx={{ mb: 2 }}
          value={username}
          onChange={e => setUsername(e.target.value)}
        />

        <TextField
          label="Пароль"
          type="password"
          fullWidth
          sx={{ mb: 2 }}
          value={password}
          onChange={e => setPassword(e.target.value)}
        />

        <Button variant="contained" fullWidth onClick={handleLogin}>
          Войти
        </Button>

        <Typography sx={{ mt: 2 }}>
          Нет аккаунта? <Link to="/register">Регистрация</Link>
        </Typography>
      </Box>
    </Container>
  );
}
