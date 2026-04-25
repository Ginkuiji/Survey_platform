import { Card, CardContent, Typography } from "@mui/material";

export default function QuestionCard({ question }) {
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6">{question.text}</Typography>
        <Typography variant="body2">{question.type}</Typography>
      </CardContent>
    </Card>
  );
}
