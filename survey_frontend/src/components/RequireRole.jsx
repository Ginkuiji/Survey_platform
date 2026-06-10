import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { fetchUserProfile } from "../api/users";

export default function RequireRole({ allowedRoles, children }) {
  const hasToken = Boolean(localStorage.getItem("accessToken"));

  const { data: user, isLoading, isError } = useQuery({
    queryKey: ["userProfile"],
    queryFn: fetchUserProfile,
    enabled: hasToken,
  });

  if (!hasToken) {
    return <Navigate to="/login" replace />;
  }

  if (isLoading) {
    return null;
  }

  if (isError || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}
