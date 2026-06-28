import { TextField, Button, Typography, Box } from "@mui/material";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { API_URL } from "../api/client";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async () => {
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/token/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.username?.[0] || "Ошибка входа");
      }

      localStorage.setItem("accessToken", data.access);
      localStorage.setItem("refreshToken", data.refresh);

      const meRes = await fetch(`${API_URL}/users/me/`, {
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
        navigate("/management/dashboard");
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
    <Box
      sx={{
        minHeight: "100vh",
        width: "100vw",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <Box
        sx={{
          width: "100%",
          maxWidth: 400,
          px: 2,
        }}
      >
        
        <Typography variant="h4" sx={{ mb: 3 }}>
          Вход
        </Typography>

        <TextField
          label="Логин"
          type="text"
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

        <Button variant="contained" fullWidth onClick={handleLogin} disabled={loading}>
          {loading ? "Вход..." : "Войти"}
        </Button>

        {error && (
          <Typography color="error" sx={{mt: 2, textAlign: "center"}}>
            {error}
          </Typography>
        )}

        <Typography sx={{ mt: 2 }}>
          Нет аккаунта? <Link to="/register">Регистрация</Link>
        </Typography>
      </Box>
    </Box>
  );
}
