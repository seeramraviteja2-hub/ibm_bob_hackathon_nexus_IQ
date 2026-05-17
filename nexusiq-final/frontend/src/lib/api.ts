import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Attach Bearer token from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return config;
});

// On 401, clear auth state and redirect to login
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      const pathname = window.location.pathname;
      if (!pathname.startsWith("/auth")) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("role");
        localStorage.removeItem("user_id");
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(err);
  }
);

export default api;
