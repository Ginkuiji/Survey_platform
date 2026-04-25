import { Card, CardContent, TextField, Typography, Box, Button, Avatar } from "@mui/material";
import { blue } from "@mui/material/colors";

export default function UserProfileBase({
  user,
  editable = false,
  onChange = () => {},
  onBlock,
  onUnblock,
  onDelete,
  onChangeRole,
  showAdminActions = false
}) {
  const roleLabel = {
    respondent: "Респондент",
    organizer: "Организатор",
    admin: "Администратор",
  }[user.role] || user.role;
  
  return (
    <Card>
      <CardContent>


          {/* АВАТАР */}
        <Box sx={{ display: "flex", justifyContent: "center", mb: 3 }}>
          <Avatar
            sx={{ width: 100, height: 100, fontSize: 40 }}
            src={user.avatar_url || ""}
          >
            {user.first_name?.[0]}
            {user.last_name?.[0]}
          </Avatar>
        </Box>


        <TextField
          label="Email"
          fullWidth
          value={user.email}
          disabled={!editable}
          onChange={e => onChange("email", e.target.value)}
          sx={{ mb: 2 }}
        />

        <TextField
          label="Имя"
          fullWidth
          value={user.first_name}
          disabled={!editable}
          onChange={e => onChange("first_name", e.target.value)}
          sx={{ mb: 2 }}
        />

        <TextField
          label="Фамилия"
          fullWidth
          value={user.last_name}
          disabled={!editable}
          onChange={e => onChange("last_name", e.target.value)}
          sx={{ mb: 2 }}
        />


        {showAdminActions ? (
          <TextField
            select
            label="Роль"
            fullWidth
            value={user.role || "respondent"}
            onChange={e => onChange("role", e.target.value)}
            sx={{mb: 2}}
            SelectProps={{native: true}}
          >
            <option value="respondent">Респондент</option>
            <option value="organizer">Организатор</option>
            <option value="admin">Администратор</option>
          </TextField>
        ) : (
          <TextField
            label="Роль"
            fullWidth
            value={roleLabel}
            disabled
            sx={{mb: 4}}
          />
        )}


        {showAdminActions && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Дата регистрации: {user.date_joined || "-"}
            </Typography>

            <Box sx={{ display: "flex", gap: 2, mt: 2, ml: "13%" }}>

              <Button variant="contained" onClick={onChangeRole}>
                Сохранить роль
              </Button>

              {user.is_active ? (
                <Button variant="contained" color="warning" onClick={onBlock}>
                  Заблокировать
                </Button>
              ) : (
                <Button variant="contained" color="success" onClick={onUnblock}>
                  Разблокировать
                </Button>
              )}

              <Button variant="contained" color="error" onClick={onDelete}>
                Удалить пользователя
              </Button>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
