import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Attach access token from cookie on every request
api.interceptors.request.use((config) => {
  if (typeof document !== "undefined") {
    const match = document.cookie.match(/access_token=([^;]+)/);
    if (match) {
      config.headers.Authorization = `Bearer ${match[1]}`;
    }
  }
  return config;
});

export default api;

// ─── Typed API helpers ────────────────────────────────────────────────────────

export const authApi = {
  login:    (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  register: (payload: object) => api.post("/auth/register", payload),
  me:       () => api.get("/auth/me"),
  refresh:  (refresh_token: string) => api.post("/auth/refresh", { refresh_token }),
  logout:   () => api.post("/auth/logout"),
};

export const decisionsApi = {
  list:          () => api.get("/decisions/"),
  create:        (payload: object) => api.post("/decisions/", payload),
  get:           (id: string) => api.get(`/decisions/${id}`),
  updateStatus:  (id: string, status: string, notes?: string) =>
    api.patch(`/decisions/${id}/status`, { status, notes }),
};

export const documentsApi = {
  list:   () => api.get("/knowledge/"),
  search: (q: string) => api.get(`/knowledge/search?q=${encodeURIComponent(q)}`),
  upload: (form: FormData) =>
    api.post("/knowledge/upload", form, { headers: { "Content-Type": "multipart/form-data" } }),
};

export const workflowApi = {
  list:        () => api.get("/workflows/"),
  start:       (decision_id: string) => api.post("/workflows/", { decision_id }),
  get:         (id: string) => api.get(`/workflows/${id}`),
  approveTask: (workflow_id: string, task_id: string) =>
    api.post(`/workflows/${workflow_id}/tasks/${task_id}/approve`),
  rejectTask:  (workflow_id: string, task_id: string, reason?: string) =>
    api.post(`/workflows/${workflow_id}/tasks/${task_id}/reject`, { reason }),
};

export const complianceApi = {
  report: (decision_id: string) => api.get(`/compliance/report/${decision_id}`),
};

export const auditApi = {
  list:  (params?: object) => api.get("/audit/", { params }),
  trace: (decision_id: string) => api.get(`/audit/trace/${decision_id}`),
};
