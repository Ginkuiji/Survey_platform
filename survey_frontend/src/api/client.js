const API_URL = "http://127.0.0.1:8000/api";

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
      lower.includes("token") ||
      lower.includes("credentials") ||
      lower.includes("authentication") ||
      lower.includes("not authenticated") ||
      lower.includes("given token not valid")
    );
  }
  return false;
}

export async function apiFetch(path, options = {}){
  const makeRequest = async (token) => {
    return fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
  };
  let accessToken = localStorage.getItem("accessToken");
  let res = await makeRequest(accessToken);

  if (res.status == 401 ){
    try{
      accessToken = await refreshAccessToken();
      res = await makeRequest(accessToken);
    } catch (e) {
      clearAuthAndRedirect();
      throw e;
    }
  }

  if (!res.ok) {
    const text = await res.text();

    if (isAuthError(res.status, text)) {
      clearAuthAndRedirect();
      throw new Error("Session expired");
    }
    throw new Error(text || "API error");
  }

  if (res.status == 204) return null;
  return res.json();
}
