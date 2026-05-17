export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function getRole(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("role");
}

export function getUserId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("user_id");
}

export function saveAuth(data: {
  access_token: string;
  refresh_token: string;
  role: string;
  user_id: string;
}) {
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  localStorage.setItem("role", data.role);
  localStorage.setItem("user_id", data.user_id);
}

export function clearAuth() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("role");
  localStorage.removeItem("user_id");
}
