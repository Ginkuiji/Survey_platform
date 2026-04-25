import {
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  Avatar,
  Box,
  Typography,
  Divider
} from "@mui/material";
import { Link, useNavigate } from "react-router-dom";
import { fetchUserProfile } from "../api/users";
import { useEffect, useState } from "react";

const drawerWidth = 240;

function roleLabel(role) {
  switch (role) {
    case "admin":
      return "Администратор";
    case "organizer":
      return "Организатор";
    case "respondent":
      return "Респондент";
    default:
      return "";
  }
}

export default function Sidebar({ mobileOpen, onClose }) {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchUserProfile()
    .then(setUser)
    .catch(()=>{
      setUser(null);
    });
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("currentUser");
    navigate("/login");
  };

  if (!user) return null;

  const isAdmin = user.role === "admin";
  const isOrganizer = user.role === "organizer";
  const isOrganizerOrAdmin = isAdmin || isOrganizer;

  const drawerContent = (
    <Box sx={{ height: "100%" }}>
      {/* --- Верхний блок с пользователем --- */}
      <Box
        sx={{
          p: 2,
          pt: 10,
          display: "flex",
          alignItems: "center"
        }}
      >
        <Avatar
          sx={{ mr: 1, cursor: "pointer" }}
          onClick={() => navigate("/profile")}
        >
          {user.first_name?.[0] || user.username?.[0]}
        </Avatar>

        <Box>
          <Typography>{user.first_name || user.username}</Typography>
          <Typography variant="body2" color="text.secondary">
            {user.email}
          </Typography>
            <Typography variant="caption" color="primary">
              {roleLabel(user.role)}
            </Typography>
        </Box>
      </Box>

      <Divider />

      {/* --- Меню --- */}
      <List>
          <ListItemButton component={Link} to="/">
            <ListItemText primary="Опросы" />
          </ListItemButton>

          {isOrganizer && (
            <ListItemButton component={Link} to="/admin/surveys">
              <ListItemText primary="Мои опросы" />
            </ListItemButton>
          )}

          {isOrganizerOrAdmin && (
          <>
            <ListItemButton component={Link} to="/analytics/surveys">
              <ListItemText primary="Аналитика" />
            </ListItemButton>

            <ListItemButton component={Link} to="/create">
              <ListItemText primary="Создать опрос" />
            </ListItemButton>

            <ListItemButton component={Link} to="/">
              <ListItemText primary="Пройти опрос" />
            </ListItemButton>
          </>
          )}

          {isAdmin && (
            <>
              <ListItemButton component={Link} to="/admin/dashboard">
                <ListItemText primary="Админ-панель" />
              </ListItemButton>

              <ListItemButton component={Link} to="/admin/users">
                <ListItemText primary="Пользователи" />
              </ListItemButton>

              <ListItemButton component={Link} to="/admin/surveys">
                <ListItemText primary="Опросы" />
              </ListItemButton>
            </>
          )}

        <Divider sx={{ my: 1 }} />

        <ListItemButton onClick={handleLogout}>
          <ListItemText primary="Выход" />
        </ListItemButton>
      </List>
    </Box>
  );

  return (
    <>
      {/* Мобильный */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", sm: "none" },
          "& .MuiDrawer-paper": { width: drawerWidth }
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Десктоп */}
      <Drawer
        variant="permanent"
        open
        sx={{
          display: { xs: "none", sm: "block" },
          "& .MuiDrawer-paper": { width: drawerWidth }
        }}
      >
        {drawerContent}
      </Drawer>
    </>
  );
}