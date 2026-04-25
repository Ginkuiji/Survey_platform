const API_URL = "http://127.0.0.1:8000/api";

async function refreshAccessToken() {
  const refresh = localStorage.getItem("refreshToken");
  if (!refresh) {
    throw new Error("No refresh token");
  }

  const res = await fetch("http://127.0.0.1:8000/api/token/refresh/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh }),
  });

  if (!res.ok) {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("currentUser");
    throw new Error("Session expired");
  }

  const data = await res.json();
  localStorage.setItem("accessToken", data.access);
  return data.access;
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
      window.location.href = "/login";
      throw e;
    }
  }

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || "API error");
  }

  if (res.status == 204) return null;
  return res.json();
}
