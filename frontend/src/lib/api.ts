import axios from "axios";

export interface ListQueryParams {
  page?: number;
  page_size?: number;
  limit?: number;
  offset?: number;
  status?: string;
  search?: string;
  entity_type?: string;
  [key: string]: string | number | boolean | null | undefined;
}

export const SESSION_EXPIRED_EVENT = "anchora:session-expired";

let handlingUnauthorized = false;

function clearAccessTokenCookie() {
  if (typeof document === "undefined") {
    return;
  }
  document.cookie = "access_token=; path=/; max-age=0; SameSite=Lax";
}

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

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      typeof window !== "undefined"
    ) {
      const currentPath = `${window.location.pathname}${window.location.search}`;
      const isAuthPath = window.location.pathname.startsWith("/login") || window.location.pathname.startsWith("/register");

      if (!isAuthPath && !handlingUnauthorized) {
        handlingUnauthorized = true;
        clearAccessTokenCookie();
        window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
        const redirectTarget = encodeURIComponent(currentPath || "/dashboard");
        window.location.assign(`/login?reason=session-expired&redirect=${redirectTarget}`);
      }
    }
    return Promise.reject(error);
  }
);

export function clearAuthSession() {
  clearAccessTokenCookie();
}

export function getApiErrorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (typeof first?.msg === "string" && first.msg.trim()) {
        return first.msg;
      }
      return detail
        .map((entry) => {
          if (typeof entry === "string") return entry;
          const candidate = (entry as { msg?: string })?.msg;
          return typeof candidate === "string" ? candidate : "";
        })
        .filter(Boolean)
        .join(", ") || fallback;
    }

    if (detail && typeof detail === "object") {
      return JSON.stringify(detail);
    }

    if (typeof error.message === "string" && error.message.trim()) {
      return error.message;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

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
  list:          (params?: ListQueryParams) => api.get("/decisions/", { params }),
  create:        (payload: object) => api.post("/decisions/", payload),
  get:           (id: string) => api.get(`/decisions/${id}`),
  updateStatus:  (id: string, status: string, notes?: string) =>
    api.patch(`/decisions/${id}/status`, { status, notes }),
  listMeetingNotes: (id: string) => api.get(`/decisions/${id}/meeting-notes`),
  createMeetingNote: (
    id: string,
    payload: {
      meeting_title?: string;
      transcript_text: string;
      execution_guidance?: string;
      action_items?: string[];
    }
  ) => api.post(`/decisions/${id}/meeting-notes`, payload),
  updateMeetingNote: (
    id: string,
    noteId: string,
    payload: {
      meeting_title?: string;
      transcript_text?: string;
      execution_guidance?: string;
      action_items?: string[];
    }
  ) => api.patch(`/decisions/${id}/meeting-notes/${noteId}`, payload),
};

export const documentsApi = {
  list:   (params?: ListQueryParams) => api.get("/knowledge/", { params }),
  search: (q: string) => api.get(`/knowledge/search?q=${encodeURIComponent(q)}`),
  upload: (form: FormData) =>
    api.post("/knowledge/upload", form, { headers: { "Content-Type": "multipart/form-data" } }),
};

export const workflowApi = {
  list:        (params?: ListQueryParams) => api.get("/workflows/", { params }),
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
  list:  (params?: ListQueryParams) => api.get("/audit/", { params }),
  trace: (decision_id: string) => api.get(`/audit/trace/${decision_id}`),
};

export const adminUsersApi = {
  listUsers: () => api.get("/admin/users"),
  listRoles: () => api.get("/admin/roles"),
  createUser: (payload: {
    email: string;
    full_name: string;
    password: string;
    role_id: string;
    is_active?: boolean;
  }) => api.post("/admin/users", payload),
  updateUser: (id: string, payload: {
    full_name?: string;
    role_id?: string;
    is_active?: boolean;
  }) => api.patch(`/admin/users/${id}`, payload),
};
