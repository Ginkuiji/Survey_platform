import { useState } from "react";
import { Box, Button, MenuItem, TextField } from "@mui/material";
import { QUESTION_TYPE_OPTIONS, QuestionType } from "../types/survey";

export default function AddQuestionMenu({ onAdd }) {
  const [qtype, setQtype] = useState(QuestionType.SINGLE);

  return (
    <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
      <TextField
        select
        label="Тип вопроса"
        size="small"
        value={qtype}
        onChange={e => setQtype(e.target.value)}
        sx={{ minWidth: 240 }}
      >
        {QUESTION_TYPE_OPTIONS.map(option => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </TextField>

      <Button variant="outlined" onClick={() => onAdd(qtype)}>
        Добавить вопрос
      </Button>
    </Box>
  );
}
