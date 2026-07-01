export const API_URL = import.meta.env.VITE_API_URL || "/api";

function clearAuthAndRedirect() {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("currentUser");

  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem("refreshToken");
  if (!refresh) {
    throw new Error("No refresh token");
  }

  const res = await fetch(`${API_URL}/token/refresh/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh }),
  });

  if (!res.ok) {
    clearAuthAndRedirect();
    throw new Error("Session expired");
  }

  const data = await res.json();
  localStorage.setItem("accessToken", data.access);
  return data.access;
}

function isAuthError(status, text) {
  if (status == 401) return true;

  if (status == 403) {
    const lower = text.toLowerCase();
    return (
      lower.includes("authentication credentials were not provided") ||
      lower.includes("not authenticated") ||
      lower.includes("invalid token") ||
      lower.includes("token not valid") ||
      lower.includes("given token not valid")
    );
  }
  return false;
}

export async function apiFetch(path, options = {}){
  const {
    responseType = "json",
    redirectOnAuthError = true,
    retryWithoutAuthOnAuthError = false,
    auth = true,
    ...fetchOptions
  } = options;
  const makeRequest = async (token) => {
    return fetch(`${API_URL}${path}`, {
      ...fetchOptions,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(fetchOptions.headers || {}),
      },
    });
  };
  let accessToken = auth ? localStorage.getItem("accessToken") : null;
  let res = await makeRequest(accessToken);

  if (res.status == 401 ){
    if (retryWithoutAuthOnAuthError && accessToken) {
      res = await makeRequest(null);
    } else if (!redirectOnAuthError) {
      throw new Error("Session expired");
    } else {
      try{
        accessToken = await refreshAccessToken();
        res = await makeRequest(accessToken);
      } catch (e) {
        clearAuthAndRedirect();
        throw e;
      }
    }
  }

  if (!res.ok) {
    const text = await res.text();

    if (isAuthError(res.status, text)) {
      if (retryWithoutAuthOnAuthError && accessToken) {
        const publicRes = await makeRequest(null);
        if (publicRes.ok) {
          if (publicRes.status == 204) return null;
          if (responseType === "blob") return publicRes.blob();
          return publicRes.json();
        }
      }
      if (redirectOnAuthError) {
        clearAuthAndRedirect();
      }
      throw new Error("Session expired");
    }
    throw new Error(text || "API error");
  }

  if (res.status == 204) return null;
  if (responseType === "blob") return res.blob();
  return res.json();
}
