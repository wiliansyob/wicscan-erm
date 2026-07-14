import { api } from "@/lib/api";

// ─── Scenario types ───────────────────────────────────────────────────────────

export interface RiskScenarioOut {
  id: string;
  project_id: string;
  scenario_code: string | null;
  title: string | null;
  consequence: string;
  group_key: string;
  asset_id?: string | null;
  asset_name?: string | null;
  business_process_id?: string | null;
  business_process_name?: string | null;
  status: string;

  // Probability
  probability?: number | null;
  prob_level?: string | null;
  probability_rationale?: string | null;

  // Impact
  impact?: number | null;
  impact_level?: string | null;
  impact_rationale?: string | null;
  impact_operational?: string | null;
  impact_financial?: string | null;
  impact_normative?: string | null;
  impact_reputational?: string | null;

  // Computed
  finding_count?: number | null;

  created_at: string;
  updated_at: string;
}

export interface ConsolidateResult {
  findings_processed: number;
  scenarios_created: number;
  scenarios_updated: number;
  scenarios: RiskScenarioOut[];
}

export interface ScenarioProbabilityUpdate {
  probability: number;
  prob_level: string;
  probability_rationale?: string | null;
}

export interface ScenarioImpactUpdate {
  business_process_id?: string | null;
  impact: number;
  impact_level: string;
  impact_rationale?: string | null;
  impact_operational?: string | null;
  impact_financial?: string | null;
  impact_normative?: string | null;
  impact_reputational?: string | null;
}

export interface ScenarioFinding {
  id: string;
  title: string;
  severity: string;
  category: string | null;
  owasp_category: string | null;
  cwe: string | null;
  description: string | null;
  file_path: string | null;
  line_start: number | null;
  asset_name: string | null;
  scanner: string | null;
  finding_type: string | null;
  confidence: number | null;
}

// ─── Risk register types ──────────────────────────────────────────────────────

export interface RiskOut {
  id: string;
  project_id: string;
  risk_code?: string | null;
  risk_title: string;
  risk_description?: string | null;
  business_impact_operational?: string | null;
  business_impact_financial?: string | null;
  business_impact_normative?: string | null;
  business_impact_reputational?: string | null;
  scenario_id?: string | null;
  probability: number;
  impact: number;
  risk_score: number;
  risk_level: string;
  prob_level?: string | null;
  impact_level?: string | null;
  impact_operational?: string | null;
  impact_financial?: string | null;
  impact_normative?: string | null;
  impact_reputational?: string | null;
  business_process_id?: string | null;
  status: string;
  assessed_by: string;
  created_at: string;
  updated_at: string;
}

// ─── API clients ──────────────────────────────────────────────────────────────

export const scenariosApi = {
  analizar: (projectId: string, findingIds?: string[], aiProvider?: string, model?: string) =>
    api.post<RiskScenarioOut[]>(`/projects/${projectId}/escenarios:analizar`, {
      ...(findingIds && findingIds.length > 0 ? { finding_ids: findingIds } : {}),
      ...(aiProvider ? { ai_provider: aiProvider } : {}),
      ...(model ? { model } : {}),
    }),

  consolidar: (projectId: string, findingIds?: string[]) =>
    api.post<ConsolidateResult>(`/projects/${projectId}/escenarios:consolidar`,
      findingIds && findingIds.length > 0 ? { finding_ids: findingIds } : {}),

  list: (projectId: string) =>
    api.get<RiskScenarioOut[]>(`/projects/${projectId}/escenarios`),

  get: (scenarioId: string) =>
    api.get<RiskScenarioOut>(`/escenarios/${scenarioId}`),

  evaluarProbabilidad: (projectId: string) =>
    api.post<RiskScenarioOut[]>(`/projects/${projectId}/escenarios:evaluar-probabilidad`),

  updateProbabilidad: (scenarioId: string, data: ScenarioProbabilityUpdate) =>
    api.patch<RiskScenarioOut>(`/escenarios/${scenarioId}/probabilidad`, data),

  updateImpacto: (scenarioId: string, data: ScenarioImpactUpdate) =>
    api.patch<RiskScenarioOut>(`/escenarios/${scenarioId}/impacto`, data),

  generarFichas: (projectId: string, aiProvider?: string, model?: string) =>
    api.post<RiskOut[]>(`/projects/${projectId}/analisis:generar-fichas`, {
      ...(aiProvider ? { ai_provider: aiProvider } : {}),
      ...(model ? { model } : {}),
    }),

  getHallazgos: (scenarioId: string) =>
    api.get<ScenarioFinding[]>(`/escenarios/${scenarioId}/hallazgos`),

  delete: (scenarioId: string) =>
    api.delete(`/escenarios/${scenarioId}`),

  aplicarCatalogo: (projectId: string) =>
    api.post<{ updated: number; skipped: number; total: number }>(
      `/projects/${projectId}/risks:aplicar-catalogo`, {}
    ),

  exportExcel: async (projectId: string, projectName: string): Promise<void> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const res = await fetch(`${baseUrl}/api/v1/projects/${projectId}/escenarios/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Error ${res.status} al generar el Excel`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `Escenarios_${projectName}_${date}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

export const riskRegisterApi = {
  list: (projectId: string) =>
    api.get<RiskOut[]>(`/projects/${projectId}/risk-register`),

  get: (riskId: string) =>
    api.get<RiskOut>(`/risks/${riskId}`),
};
