import { apiFetch } from "./client";

export const fetchUserProfile = () =>
  apiFetch("/users/me/");

export const updateUserProfile = (data) =>
  apiFetch("/users/me/", {
    method: "PATCH",
    body: JSON.stringify(data)
  });

export const fetchAllUsers = () =>
  apiFetch("/users/");

export const updateUserAdmin = (id, data) =>
  apiFetch(`/users/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data)
  });

export const fetchUserById = (id) =>
  apiFetch(`/users/${id}/`);

// мягкое удаление (рекомендуется)
export const blockUser = (id) =>
  updateUserAdmin(id, { is_active: false });

export const unblockUser = (id) =>
  updateUserAdmin(id, { is_active: true });

// если хочешь физическое удаление (необязательно)
export const deleteUser = (id) =>
  apiFetch(`/users/${id}/`, { method: "DELETE" });
