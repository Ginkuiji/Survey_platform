import { useEffect, useState } from "react";
import { Container, Typography, Button, Box } from "@mui/material";
import UserProfileBase from "../components/UserProfileBase";
import { fetchUserProfile, updateUserProfile } from "../api/users";

export default function UserProfilePage() {
  const [user, setUser] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({
    email: "",
    first_name: "",
    last_name: ""
  });

  useEffect(() => {
    fetchUserProfile().then((data) => {
      setUser(data);
      setForm({
        email: data.email || "",
        first_name: data.first_name || "",
        last_name: data.last_name || ""
      });
    });
  }, []);

  if (!user) return null;

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    await updateUserProfile(form);

    setUser((prev) => ({ ...prev, ...form }));
    setEditMode(false);
    alert("Профиль обновлён");
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Профиль пользователя
      </Typography>

      <UserProfileBase
        user={{ ...user, ...form }}
        editable={editMode}
        onChange={handleChange}
      />

      <Box sx={{ mt: 2, maxWidth: "80%" }}>
        {!editMode ? (
          <Button
            variant="contained"
            fullWidth
            onClick={() => setEditMode(true)}
            sx={{ ml: "13%" }}
          >
            Редактировать
          </Button>
        ) : (
          <Box sx={{ display: "flex", ml: "30%" }}>
            <Button
              variant="contained"
              sx={{ mb: 2, width: "500%", mr: "5%" }}
              onClick={handleSave}
            >
              Сохранить
            </Button>

            <Button
              variant="outlined"
              sx={{ width: "500%" }}
              onClick={() => {
                setForm({
                  email: user.email || "",
                  first_name: user.first_name || "",
                  last_name: user.last_name || ""
                });
                setEditMode(false);
              }}
            >
              Отмена
            </Button>
          </Box>
        )}
      </Box>
    </Container>
  );
}
