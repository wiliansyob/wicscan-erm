import axios, { AxiosInstance } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// Inject JWT token on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global 401 handler
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (
      error.response?.status === 401 &&
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/login") &&
      !window.location.pathname.startsWith("/register")
    ) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ─── Auth ───────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  register: (data: { workspace_name: string; email: string; password: string; full_name: string }) =>
    api.post("/auth/register", data),
  me: () => api.get("/auth/me"),
};

// ─── Projects ───────────────────────────────────────────────────
export const projectsApi = {
  list: (params?: { page?: number; size?: number; status?: string }) =>
    api.get("/projects", { params }),
  get: (id: string) => api.get(`/projects/${id}`),
  create: (data: object) => api.post("/projects", data),
  update: (id: string, data: object) => api.patch(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),
};

// ─── Assets ─────────────────────────────────────────────────────
export const assetsApi = {
  list: (projectId: string, params?: object) =>
    api.get(`/projects/${projectId}/assets`, { params }),
  get: (id: string) => api.get(`/assets/${id}`),
  create: (projectId: string, data: object) =>
    api.post(`/projects/${projectId}/assets`, data),
  update: (id: string, data: object) => api.patch(`/assets/${id}`, data),
  delete: (id: string) => api.delete(`/assets/${id}`),
};

// ─── Code Sources ────────────────────────────────────────────────
export const codeSourcesApi = {
  list: (projectId: string, assetId?: string) =>
    api.get(`/projects/${projectId}/code-sources`, { params: assetId ? { asset_id: assetId } : {} }),
  get: (id: string) => api.get(`/code-sources/${id}`),
  create: (projectId: string, data: {
    source_type: "github" | "zip";
    label: string;
    asset_id?: string;
    github_url?: string;
    github_branch?: string;
    github_token?: string;
    zip_filename?: string;
  }) => api.post(`/projects/${projectId}/code-sources`, data),
  uploadZip: (projectId: string, file: File, opts: { label?: string; asset_id?: string }) => {
    const form = new FormData();
    form.append("file", file);
    if (opts.label) form.append("label", opts.label);
    if (opts.asset_id) form.append("asset_id", opts.asset_id);
    return api.post(`/projects/${projectId}/code-sources/upload`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  delete: (id: string) => api.delete(`/code-sources/${id}`),
};

// ─── Scan Sessions ───────────────────────────────────────────────
export const scanSessionsApi = {
  list: (projectId: string, params?: { page?: number; size?: number; asset_id?: string }) =>
    api.get(`/projects/${projectId}/scan-sessions`, { params }),
  get: (id: string) => api.get(`/scan-sessions/${id}`),
  create: (projectId: string, data: {
    code_source_id?: string;
    asset_id?: string;
    scanners?: string[];
    scanner_configs?: Record<string, any>;
    is_retest?: boolean;
    baseline_session_id?: string;
  }) => api.post(`/projects/${projectId}/scan-sessions`, data),
  cancel: (id: string) => api.patch(`/scan-sessions/${id}/cancel`),
  delete: (id: string) => api.delete(`/scan-sessions/${id}`),
  listScans: (id: string) => api.get(`/scan-sessions/${id}/scans`),
};

// ─── Scans ──────────────────────────────────────────────────────
export const scansApi = {
  get: (id: string) => api.get(`/scans/${id}`),
  list: (params?: { session_id?: string; status?: string }) =>
    api.get("/scans", { params }),
};

// ─── Findings ───────────────────────────────────────────────────
export const findingsApi = {
  list: (params?: {
    project_id?: string;
    asset_id?: string;
    severity?: string[];
    status?: string;
    scanner?: string;
    scan_session_id?: string;
    page?: number;
    size?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") return;
        if (Array.isArray(value)) {
          if (value.length > 0) value.forEach(v => searchParams.append(key, v.toString()));
        } else {
          searchParams.append(key, value.toString());
        }
      });
    }
    return api.get("/findings", { params: searchParams });
  },
  summary: (params?: { project_id?: string; asset_id?: string }) =>
    api.get("/findings/stats/summary", { params }),
  sources: (params?: { project_id?: string; asset_id?: string; status?: string }) =>
    api.get("/findings/stats/sources", { params }),
  get: (id: string) => api.get(`/findings/${id}`),
  updateStatus: (id: string, status: string, reason?: string) =>
    api.patch(`/findings/${id}/status`, { status, reason }),
  update: (id: string, data: object) => api.patch(`/findings/${id}`, data),
  delete: (id: string) => api.delete(`/findings/${id}`),
  getSnippet: (id: string) => api.get(`/findings/${id}/snippet`),
  createManual: (data: any) => api.post("/findings/manual", data),
  uploadCsv: (assetId: string, file: File) => {
    const form = new FormData();
    form.append("asset_id", assetId);
    form.append("file", file);
    return api.post("/findings/upload-csv", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

// ─── Risks ──────────────────────────────────────────────────────
export const risksApi = {
  list: (params?: {
    project_id?: string;
    asset_id?: string;
    risk_level?: string;
    status?: string;
    page?: number;
    size?: number;
  }) => api.get("/risks", { params }),
  get: (id: string) => api.get(`/risks/${id}`),
  create: (projectId: string, data: object) =>
    api.post("/risks", data, { params: { project_id: projectId } }),
  update: (id: string, data: object) => api.patch(`/risks/${id}`, data),
  getMatrix: (projectId?: string, assetId?: string) =>
    api.get("/risks/matrix", { params: { ...(projectId ? { project_id: projectId } : {}), ...(assetId ? { asset_id: assetId } : {}) } }),
  confirm: (id: string) => api.patch(`/risks/${id}/confirm`),
  accept: (id: string) => api.patch(`/risks/${id}/accept`),
  addTreatment: (riskId: string, data: object) =>
    api.post(`/risks/${riskId}/treatments`, data),
  updateTreatment: (treatmentId: string, data: object) =>
    api.patch(`/risks/treatments/${treatmentId}`, data),
  deleteTreatment: (treatmentId: string) =>
    api.delete(`/risks/treatments/${treatmentId}`),
  listTreatments: (riskId: string) =>
    api.get(`/risks/${riskId}/treatments`),
  delete: (id: string) => api.delete(`/risks/${id}`),
  merge: (riskIds: string[], keepId?: string) =>
    api.post("/risks/merge", { risk_ids: riskIds, keep_id: keepId }),
  suggestTreatments: (riskId: string, aiProvider: string, model?: string) =>
    api.post(`/risks/${riskId}/treatments/suggest`, { ai_provider: aiProvider, model }),
  exportTreatmentsExcel: async (projectId: string, projectName: string): Promise<void> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const res = await fetch(`${baseUrl}/api/v1/treatments/projects/${projectId}/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Error ${res.status} al generar el Excel`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safeName = projectName.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    a.href = url;
    a.download = `Plan_Tratamiento_${safeName}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

// ─── Risk Engine ─────────────────────────────────────────────────
export const riskEngineApi = {
  trigger: (projectId: string, data: {
    scan_session_id: string;
    finding_ids?: string[];
    ai_provider: string;
    model_used?: string;
    prompt_template?: string;
  }) => api.post("/risk-engine/runs", data, { params: { project_id: projectId } }),
  listRuns: (projectId: string, assetId?: string) =>
    api.get("/risk-engine/runs", { params: { project_id: projectId, ...(assetId ? { asset_id: assetId } : {}) } }),
  getRun: (id: string) => api.get(`/risk-engine/runs/${id}`),
  deleteRiskEngineRun: (id: string) => api.delete(`/risk-engine/runs/${id}`),
};

// ─── Workspaces ──────────────────────────────────────────────────
export const workspacesApi = {
  getSettings: () => api.get("/workspaces/settings"),
  updateSettings: (data: { ai_config: { anthropic_api_key?: string; openai_api_key?: string; gemini_api_key?: string; custom_api_key?: string; ollama_url?: string; risk_config?: any; report_config?: any } }) => 
    api.patch("/workspaces/settings", data),
};

// ─── Scanners ────────────────────────────────────────────────────
export const scannersApi = {
  list: () => api.get("/scanners"),
  create: (data: { name: string; engine_type: string; url: string; api_key?: string; is_active?: boolean }) => 
    api.post("/scanners", data),
  update: (id: string, data: any) => api.put(`/scanners/${id}`, data),
  delete: (id: string) => api.delete(`/scanners/${id}`),
};

// ─── ISO 31000: Catalog & Questionnaire ──────────────────────────
export const catalogApi = {
  list: () => api.get("/admin/questionnaire-definitions"),
  createDraft: () => api.post("/admin/questionnaire-definitions"),
  get: (id: string) => api.get(`/admin/questionnaire-definitions/${id}`),
  publish: (id: string) => api.post(`/admin/questionnaire-definitions/${id}/publish`),
};

// ─── ISO 31000: BIA ────────────────────────────────────────────────
export const biaApi = {
  listProcesses: (projectId: string) => api.get(`/projects/${projectId}/processes`),
  createProcess: (projectId: string, data: any) => api.post(`/projects/${projectId}/processes`, data),
};
