import { AppBar, Toolbar, IconButton, Typography, TextField, Box } from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";

export default function Topbar({ onMenuClick, onSearch }) {
  return (
    <AppBar position="fixed" sx={{ zIndex: theme => theme.zIndex.drawer + 1 }}>
      <Toolbar>

        {/* Кнопка меню (мобильные устройства) */}
        <IconButton
          color="inherit"
          edge="start"
          onClick={onMenuClick}
          sx={{ mr: 2, display: { sm: "none" } }}
        >
          <MenuIcon />
        </IconButton>

        {/* Название платформы */}
        <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
          Платформа для проведения опросов
        </Typography>

        {/* Поле поиска
        <Box sx={{ width: 260 }}>
          <TextField
            size="small"
            placeholder="Поиск…"
            variant="outlined"
            fullWidth
            onChange={e => onSearch && onSearch(e.target.value)}
            sx={{
              bgcolor: "white",
              borderRadius: 1,
              "& .MuiOutlinedInput-root": {
                height: 36,
                paddingRight: 0
              }
            }}
          />
        </Box> */}

      </Toolbar>
    </AppBar>
  );
}
