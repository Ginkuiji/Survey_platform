import { Container, Typography } from "@mui/material";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, useEffect } from "react";

import UserProfileBase from "../components/UserProfileBase";
import {
  fetchUserById,
  updateUserAdmin,
  blockUser,
  unblockUser,
  deleteUser,
} from "../api/users";

export default function AdminUserProfilePage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: user, isLoading } = useQuery({
    queryKey: ["user", id],
    queryFn: () => fetchUserById(id),
  });

  const [form, setForm] = useState(null);

  useEffect(() => {
    if (user) setForm({ ...user });
  }, [user]);

  const updateMutation = useMutation({
    mutationFn: (data) => updateUserAdmin(id, data),
  });

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveRole = () => {
    updateMutation.mutate(
      {
        role: form.role,
      },
      {
        onSuccess: (updatedUser) => {
          setForm(updatedUser);
          alert("Права пользователя обновлены");
        },
      }
    );
  };

  const handleBlock = async () => {
    const updatedUser = await blockUser(id);
    setForm(updatedUser);
  };

  const handleUnblock = async () => {
    const updatedUser = await unblockUser(id);
    setForm(updatedUser);
  };

  const handleDelete = async () => {
    await deleteUser(id);
    navigate("/admin/users");
  };

  if (isLoading || !form) return null;

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Профиль пользователя
      </Typography>

      <UserProfileBase
        user={form}
        editable={false}
        showAdminActions={true}
        onChange={handleChange}
        onBlock={handleBlock}
        onUnblock={handleUnblock}
        onDelete={handleDelete}
        onChangeRole={handleSaveRole}
      />
    </Container>
  );
}