import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
  // Set a longer timeout for AI course generation (60s)
  timeout: 60000, 
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

/**
 * COURSE MANAGEMENT FUNCTIONS
 */

// Delete a specific course
export const deleteCourse = async (courseId: string) => {
  try {
    const response = await api.delete(`/api/v1/manager/courses/${courseId}`);
    return response.data;
  } catch (error) {
    console.error("Error deleting course:", error);
    throw error;
  }
};

// Fetch manager courses (to refresh UI after deletion)
export const getManagerCourses = async () => {
  const response = await api.get("/api/v1/manager/courses");
  return response.data;
};

export default api;
