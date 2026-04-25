import { Container, TextField, Button, Typography, Box } from "@mui/material";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password1, setPassword1] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleRegister = async () => {
    setError("");
    setSuccess("");

    if (password1 !== password2) {
      setError("Пароли не совпадают");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/auth/register/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          username,
          password1,
          password2,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        if (typeof data === "object") {
          const firstError =
            data.email?.[0] ||
            data.username?.[0] ||
            data.password1?.[0] ||
            data.password2?.[0] ||
            data.non_field_errors?.[0] ||
            data.detail ||
            "Ошибка регистрации";
          throw new Error(firstError);
        }
        throw new Error("Ошибка регистрации");
      }

      setSuccess("Регистрация выполнена");
      navigate("/login");
    } catch (err) {
      setError(err.message || "Ошибка регистрации");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container sx={{ mt: 6, display: "flex", flexDirection: "column", alignItems: "center" }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Регистрация
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
          value={password1}
          onChange={e => setPassword1(e.target.value)}
        />

        <TextField
          label="Повторите пароль"
          type="password"
          fullWidth
          sx={{ mb: 2 }}
          value={password2}
          onChange={e => setPassword2(e.target.value)}
        />

        <Button variant="contained" fullWidth onClick={handleRegister} disabled={loading}>
          {loading? "Регистрация..." : "Зарегистрироваться"}
        </Button>

        <Typography sx={{ mt: 2 }}>
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </Typography>
      </Box>
    </Container>
  );
}
