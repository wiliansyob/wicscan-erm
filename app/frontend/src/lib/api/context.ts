import { api } from "@/lib/api";

// ─── BIA types ────────────────────────────────────────────────────────────────

export interface BusinessProcessIn {
  name: string;
  owner_name?: string | null;
  criticality: string;
  revenue_dependency: string;
  has_manual_alternative: boolean;
  contractual_commitments: boolean;
  notes?: string | null;
}

export interface BusinessProcessOut {
  id: string;
  project_id: string;
  name: string;
  owner_name?: string | null;
  criticality: string;
  revenue_dependency: string;
  has_manual_alternative: boolean;
  contractual_commitments: boolean;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BiaCalculateIn {
  num_staff_affected?: number | null;
  avg_salary_hour?: number | null;
  infra_cost_per_hour?: number | null;
  contractual_penalty_per_hour?: number | null;
  sla_at_risk_value?: number | null;
  hourly_revenue?: number | null;
  revenue_dependency_pct?: number | null;
  sn_active?: boolean;
  sanction_amount?: number | null;
  annual_revenue?: number | null;
  mtpd_hours?: number | null;
  rto_hours?: number | null;
  rpo_hours?: number | null;
}

export interface BiaEstimateOut {
  id: string;
  process_id: string;
  impact_2h: number;
  impact_8h: number;
  impact_24h: number;
  sn_active: boolean;
  mtpd_hours?: number | null;
  rto_hours?: number | null;
  rpo_hours?: number | null;
  breakdown: Record<string, unknown>;
  created_at: string;
}

export interface AssetProcessLinkIn {
  asset_id: string;
  weight: number;
}

export interface AssetProcessLinkOut {
  id: string;
  process_id: string;
  asset_id: string;
  weight: number;
  asset_name?: string | null;
  asset_type?: string | null;
  asset_criticality?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BusinessProcessWithBiaOut extends BusinessProcessOut {
  bia?: BiaEstimateOut | null;
  asset_links: AssetProcessLinkOut[];
}

// ─── API clients ──────────────────────────────────────────────────────────────

export interface AssetSimpleOut {
  id: string;
  name: string;
  asset_type: string;
  criticality: string;
}

export const biaApi = {
  listProcesses: (projectId: string) =>
    api.get<BusinessProcessWithBiaOut[]>(`/projects/${projectId}/processes`),

  createProcess: (projectId: string, data: BusinessProcessIn) =>
    api.post<BusinessProcessOut>(`/projects/${projectId}/processes`, data),

  updateProcess: (processId: string, data: BusinessProcessIn) =>
    api.put<BusinessProcessOut>(`/processes/${processId}`, data),

  deleteProcess: (processId: string) =>
    api.delete(`/processes/${processId}`),

  calculateBia: (processId: string, data: BiaCalculateIn) =>
    api.post<BiaEstimateOut>(`/processes/${processId}/bia`, data),

  getBia: (processId: string) =>
    api.get<BiaEstimateOut>(`/processes/${processId}/bia`),

  listAssets: (projectId: string) =>
    api.get<{ items: AssetSimpleOut[] }>(`/projects/${projectId}/assets?limit=200`),

  upsertAssetLink: (processId: string, assetId: string, weight: number) =>
    api.put<AssetProcessLinkOut>(`/processes/${processId}/asset-links/${assetId}`, {
      asset_id: assetId,
      weight,
    }),

  removeAssetLink: (processId: string, assetId: string) =>
    api.delete(`/processes/${processId}/asset-links/${assetId}`),

  exportExcel: async (projectId: string, projectName: string): Promise<void> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const res = await fetch(`${baseUrl}/api/v1/projects/${projectId}/processes/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Error ${res.status} al generar el Excel`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `BIA_${projectName}_${date}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  exportVulnExcel: async (projectId: string, projectName: string): Promise<void> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const res = await fetch(`${baseUrl}/api/v1/projects/${projectId}/vulnerabilities/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Error ${res.status} al generar el Excel`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `Vulnerabilidades_${projectName}_${date}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

