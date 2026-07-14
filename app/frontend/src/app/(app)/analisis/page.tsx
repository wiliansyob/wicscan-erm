"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { risksApi, findingsApi, workspacesApi, biaApi } from "@/lib/api";
import { scenariosApi as scenariosApiExt } from "@/lib/api/assessment";
import { useProjectStore } from "@/lib/project";
import {
  BarChart3, Save, Loader, ChevronDown, ChevronUp,
  MessageSquare, Trash2, Code, Copy, GitMerge, CheckSquare,
  Square, X, ShieldAlert, AlertTriangle, Layers, Brain, Zap, Download, BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";

const DEFAULT_AI_PROVIDERS = [
  { value: "anthropic", label: "Anthropic Claude", models: ["claude-3-5-sonnet-20241022"] },
  { value: "gemini",    label: "Google Gemini",    models: ["gemini-flash-latest"] },
  { value: "ollama",    label: "Ollama (local)",   models: ["llama3.2"] },
];

import { DEFAULT_RISK_CONFIG, RiskCriteriaTab } from "@/components/risks/risk-criteria";
import { RiskHeatmap } from "@/components/risks/risk-heatmap";

const TABS = ["Mapa de riesgo", "Generar fichas RN-xxx", "Criterios de Riesgo"] as const;
type Tab = typeof TABS[number];

const LEVEL_BG: Record<string, string> = {
  critical: "bg-red-600",
  high:     "bg-orange-500",
  medium:   "bg-yellow-400",
  low:      "bg-[#2FCC4C]",
};
const LEVEL_TEXT: Record<string, string> = {
  critical: "text-red-700 bg-red-50 border-red-200",
  high:     "text-orange-700 bg-orange-50 border-orange-200",
  medium:   "text-yellow-700 bg-yellow-50 border-yellow-200",
  low:      "text-green-700 bg-green-50 border-green-200",
};
const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:      "bg-blue-100 text-blue-700 border-blue-200",
  info:     "bg-gray-100 text-gray-500 border-gray-200",
};
const IMPACT_COLOR: Record<string, string> = {
  "Muy Alto":  "text-red-700 bg-red-50 border-red-200",
  "Alto":      "text-orange-700 bg-orange-50 border-orange-200",
  "Medio":     "text-yellow-700 bg-yellow-50 border-yellow-200",
  "Bajo":      "text-green-700 bg-green-50 border-green-200",
  "Muy Bajo":  "text-gray-500 bg-gray-50 border-gray-200",
};
const PRIORITY_LABELS: Record<string, string> = {
  immediate: "Inmediato", short_term: "Corto plazo", medium_term: "Mediano plazo", long_term: "Largo plazo",
};
const SCANNER_LABEL: Record<string, { label: string; cls: string }> = {
  sonarqube: { label: "SAST",    cls: "bg-purple-100 text-purple-700 border-purple-200" },
  zap:       { label: "DAST",    cls: "bg-blue-100 text-blue-700 border-blue-200" },
  burp:      { label: "DAST",    cls: "bg-blue-100 text-blue-700 border-blue-200" },
  manual:    { label: "Manual",  cls: "bg-gray-100 text-gray-600 border-gray-300" },
  ethical:   { label: "Ethical", cls: "bg-teal-100 text-teal-700 border-teal-200" },
  nessus:    { label: "VA",      cls: "bg-indigo-100 text-indigo-700 border-indigo-200" },
  openvas:   { label: "VA",      cls: "bg-indigo-100 text-indigo-700 border-indigo-200" },
};
function scannerBadge(scanner?: string | null) {
  if (!scanner) return null;
  const key = scanner.toLowerCase();
  const meta = SCANNER_LABEL[key] ?? { label: scanner.toUpperCase(), cls: "bg-gray-100 text-gray-600 border-gray-300" };
  return <span className={cn("text-[10px] px-1.5 py-0.5 rounded border font-semibold flex-shrink-0 mt-0.5 leading-tight", meta.cls)}>{meta.label}</span>;
}

function ImpactBadge({ label, value }: { label: string; value?: string | null }) {
  if (!value) return (
    <div className="text-center">
      <p className="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">{label}</p>
      <span className="text-xs text-gray-300">—</span>
    </div>
  );
  return (
    <div className="text-center">
      <p className="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">{label}</p>
      <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded border", IMPACT_COLOR[value] ?? "text-gray-500 bg-gray-50 border-gray-200")}>
        {value}
      </span>
    </div>
  );
}

export default function AnalisisPage() {
  const qc = useQueryClient();
  const { project, assetId } = useProjectStore();

  const [tab, setTab]             = useState<Tab>("Mapa de riesgo");
  const [editingId, setEditingId]             = useState<string | null>(null);
  const [expandedHallazgos, setExpandedHallazgos] = useState<Set<string>>(new Set());
  const [editForm, setEditForm]   = useState({ probability: 3, impact: 3, rationale: "", priority: "medium_term" });
  const [mergeMode, setMergeMode]         = useState(false);
  const [selectedMerge, setSelectedMerge] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<string | null>(null);
  const [aiProvider, setAiProvider] = useState("gemini");
  const [aiModel, setAiModel]       = useState("");

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  };

  const { data: matrixData } = useQuery({
    queryKey: ["risk-matrix", project?.id],
    queryFn: () => risksApi.getMatrix(project?.id, undefined).then(r => r.data),
    enabled: !!project,
  });

  const { data: settingsData } = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: () => workspacesApi.getSettings().then(res => res.data),
  });

  const riskConfig = settingsData?.ai_config?.risk_config || DEFAULT_RISK_CONFIG;

  const availableProviders: { value: string; label: string; models: string[] }[] = (() => {
    const config = settingsData?.ai_config;
    if (!config) return [];
    const list: { value: string; label: string; models: string[] }[] = [];
    const parseModels = (modelStr?: string, def = "Default") =>
      (modelStr || def).split(",").map((m: string) => m.trim()).filter(Boolean);
    if (config.providers) {
      Object.keys(config.providers).forEach(key => {
        const prov = config.providers[key];
        if (!prov) return;
        if (key.startsWith("custom_")) {
          if (prov.enabled && prov.api_key && prov.url)
            list.push({ value: key, label: prov.label || "Custom", models: parseModels(prov.model) });
        } else if (key === "ollama") {
          if (prov.enabled) list.push({ value: key, label: "Ollama (local)", models: parseModels(prov.model, "llama3.2") });
        } else if (prov.enabled && prov.api_key) {
          const match = DEFAULT_AI_PROVIDERS.find(p => p.value === key);
          if (match) list.push({ ...match, models: parseModels(prov.model, match.models[0]) });
        }
      });
      return list;
    }
    DEFAULT_AI_PROVIDERS.forEach(p => {
      if (config[`${p.value}_api_key`]) list.push({ ...p });
    });
    return list;
  })();

  useEffect(() => {
    if (availableProviders.length > 0) {
      const current = availableProviders.find(p => p.value === aiProvider) ?? availableProviders[0];
      if (!availableProviders.find(p => p.value === aiProvider)) setAiProvider(current.value);
      if (current.models.length > 0 && !current.models.includes(aiModel)) setAiModel(current.models[0]);
    }
  }, [settingsData]);

  const { data: risksData, isLoading } = useQuery({
    queryKey: ["risks", project?.id],
    queryFn: () => risksApi.list({
      project_id: project?.id,
      size: 100,
    }).then(r => r.data),
    enabled: !!project,
  });

  const { data: processesData } = useQuery({
    queryKey: ["bia-processes", project?.id],
    queryFn: () => biaApi.listProcesses(project!.id).then(r => r.data),
    enabled: !!project,
  });

  const { data: allFindingsData } = useQuery({
    queryKey: ["findings-analisis", project?.id],
    queryFn: () => findingsApi.list({
      project_id: project?.id,
      size: 500,
    }).then(r => r.data),
    enabled: !!project,
  });

  const { data: scenariosData } = useQuery({
    queryKey: ["scenarios", project?.id],
    queryFn: () => scenariosApiExt.list(project!.id).then(r => r.data),
    enabled: !!project,
  });

  const generateFromScenariosMut = useMutation({
    mutationFn: () => scenariosApiExt.generarFichas(project!.id, aiProvider, aiModel || undefined).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risks"] });
      qc.invalidateQueries({ queryKey: ["risk-matrix"] });
      qc.invalidateQueries({ queryKey: ["scenarios", project?.id] });
      showToast("Riesgos generados desde escenarios P×I");
    },
  });

  const aplicarCatalogoMut = useMutation({
    mutationFn: () => scenariosApiExt.aplicarCatalogo(project!.id).then((r: { data: { updated: number; skipped: number; total: number } }) => r.data),
    onSuccess: (data: { updated: number; skipped: number; total: number }) => {
      qc.invalidateQueries({ queryKey: ["risks"] });
      qc.invalidateQueries({ queryKey: ["risk-matrix"] });
      qc.invalidateQueries({ queryKey: ["scenarios", project?.id] });
      showToast(`Catálogo aplicado: ${data.updated} riesgos renombrados`);
    },
  });

  const { data: snippetData, isLoading: snippetLoading } = useQuery({
    queryKey: ["finding-snippet", editingId],
    queryFn: () => {
      const risk = (risksData?.items as any[])?.find((r: any) => r.id === editingId);
      if (risk?.finding_ids?.length > 0) {
        return findingsApi.getSnippet(risk.finding_ids[0]).then(r => r.data);
      }
      return null;
    },
    enabled: !!editingId && !!(risksData?.items as any[])?.length,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id }: { id: string }) =>
      risksApi.update(id, {
        probability: editForm.probability,
        impact: editForm.impact,
        likelihood_rationale: editForm.rationale || undefined,
        priority: editForm.priority || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risks"] });
      qc.invalidateQueries({ queryKey: ["risk-matrix"] });
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => risksApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risks"] });
      qc.invalidateQueries({ queryKey: ["risk-matrix"] });
      qc.invalidateQueries({ queryKey: ["scenarios", project?.id] });
      showToast("Riesgo eliminado. El escenario vuelve a pendiente.");
    },
  });

  const mergeMutation = useMutation({
    mutationFn: (ids: string[]) => risksApi.merge(ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risks"] });
      qc.invalidateQueries({ queryKey: ["risk-matrix"] });
      setMergeMode(false);
      setSelectedMerge(new Set());
      showToast("Riesgos fusionados correctamente");
    },
  });

  const matrix: number[][] = matrixData?.matrix ?? Array.from({ length: 5 }, () => Array(5).fill(0));
  const riskPositions: any[] = matrixData?.risks ?? [];
  const summary = matrixData?.summary ?? {};

  const risks: any[] = [...(risksData?.items ?? [])].sort((a, b) => {
    const sa = a.risk_score || (a.probability * a.impact) || 0;
    const sb = b.risk_score || (b.probability * b.impact) || 0;
    return sb - sa;
  });
  const allFindings: any[] = allFindingsData?.items ?? [];
  const processes: any[] = processesData ?? [];

  // Agrupar riesgos por proceso de negocio
  const processMap = new Map<string, any>(processes.map(p => [p.id, p]));

  type RiskGroup = { process: any | null; risks: any[] };
  const grouped: RiskGroup[] = [];
  const seenProcessIds = new Set<string>();

  // Primero: grupos con proceso asignado (orden por criticidad de proceso)
  const critOrder: Record<string, number> = { critical: 0, important: 1, support: 2 };
  const sortedProcesses = [...processes].sort(
    (a, b) => (critOrder[a.criticality] ?? 3) - (critOrder[b.criticality] ?? 3)
  );

  for (const proc of sortedProcesses) {
    const procRisks = risks.filter(r => r.business_process_id === proc.id);
    if (procRisks.length > 0) {
      grouped.push({ process: proc, risks: procRisks });
      seenProcessIds.add(proc.id);
    }
  }

  // Al final: riesgos sin proceso asignado
  const unlinkedRisks = risks.filter(r => !r.business_process_id || !seenProcessIds.has(r.business_process_id));
  if (unlinkedRisks.length > 0) {
    grouped.push({ process: null, risks: unlinkedRisks });
  }

  const toggleMergeSelect = (id: string) => {
    setSelectedMerge(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const CRIT_LABEL: Record<string, string> = { critical: "Crítico", important: "Importante", support: "Soporte" };
  const CRIT_COLOR: Record<string, string> = {
    critical:  "text-red-700 bg-red-50 border-red-200",
    important: "text-orange-700 bg-orange-50 border-orange-200",
    support:   "text-gray-600 bg-gray-50 border-gray-200",
  };

  function RiskCard({ risk }: { risk: any }) {
    const isEditing = editingId === risk.id;
    const isMergeSelected = selectedMerge.has(risk.id);
    const showHallazgos = expandedHallazgos.has(risk.id);
    const riskEvidence = allFindings.filter((f: any) => (risk.finding_ids ?? []).includes(f.id));
    const toggleHallazgos = () => setExpandedHallazgos(prev => {
      const next = new Set(prev);
      next.has(risk.id) ? next.delete(risk.id) : next.add(risk.id);
      return next;
    });

    return (
      <div
        key={risk.id}
        id={`risk-${risk.id}`}
        className={cn(
          "bg-white border rounded-xl overflow-hidden transition-all",
          isEditing       ? "border-blue-400 shadow-sm" :
          isMergeSelected ? "border-purple-400 bg-purple-50/30" :
          "border-gray-200"
        )}
      >
        {/* ── Fila principal: badge + título + scores ── */}
        <div className="flex items-center gap-3 px-4 py-3">
          {mergeMode && (
            <button onClick={() => toggleMergeSelect(risk.id)} className="flex-shrink-0 text-purple-500 hover:text-purple-700">
              {isMergeSelected ? <CheckSquare size={18} /> : <Square size={18} className="text-gray-300" />}
            </button>
          )}

          <span className={cn("text-xs font-bold px-2 py-1 rounded text-white flex-shrink-0", LEVEL_BG[risk.risk_level])}>
            {risk.risk_code ?? "R-?"}
          </span>

          <p className="flex-1 min-w-0 text-sm font-medium text-gray-900 truncate">{risk.risk_title}</p>

          {/* P×I Score compacto */}
          <div className="flex items-center gap-2 text-xs flex-shrink-0">
            <span className="text-gray-400">P</span>
            <span className="font-bold text-gray-800">{risk.probability}</span>
            <span className="text-gray-300">×</span>
            <span className="text-gray-400">I</span>
            <span className="font-bold text-gray-800">{risk.impact}</span>
            <span className="text-gray-300">=</span>
            <span className={cn("font-bold text-base", {
              "text-red-600":    risk.risk_level === "critical",
              "text-orange-500": risk.risk_level === "high",
              "text-yellow-600": risk.risk_level === "medium",
              "text-green-600":  risk.risk_level === "low",
            })}>{risk.risk_score}</span>
          </div>

          {isEditing && (
            <button onClick={() => setEditingId(null)} className="text-gray-400 hover:text-gray-600 flex-shrink-0">
              <X size={15} />
            </button>
          )}
        </div>

        {/* ── Footer: dimensiones + acciones ── */}
        {!isEditing && (
          <div className="flex items-center justify-between px-4 py-2 border-t border-gray-100 bg-gray-50/40">
            {/* Dimensiones de impacto */}
            <div className="flex items-center gap-3 min-w-0">
              {(risk.impact_operational || risk.impact_financial || risk.impact_normative || risk.impact_reputational) ? (
                <>
                  <ImpactBadge label="Oper."  value={risk.impact_operational} />
                  <ImpactBadge label="Fin."   value={risk.impact_financial} />
                  <ImpactBadge label="Norm."  value={risk.impact_normative} />
                  <ImpactBadge label="Rep."   value={risk.impact_reputational} />
                </>
              ) : (
                risk.priority && (
                  <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded", {
                    "bg-orange-50 text-orange-600": risk.priority === "immediate",
                    "bg-yellow-50 text-yellow-600": risk.priority === "short_term",
                    "bg-blue-50 text-blue-600":     risk.priority === "medium_term",
                    "bg-gray-100 text-gray-500":    risk.priority === "long_term",
                  })}>
                    {PRIORITY_LABELS[risk.priority]}
                  </span>
                )
              )}
            </div>

            {/* Acciones */}
            {!mergeMode && (
              <div className="flex items-center gap-1 flex-shrink-0">
                {riskEvidence.length > 0 && (
                  <button
                    onClick={toggleHallazgos}
                    className={cn(
                      "flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors",
                      showHallazgos
                        ? "bg-orange-100 text-orange-700"
                        : "text-gray-400 hover:text-orange-600 hover:bg-orange-50"
                    )}
                  >
                    <ShieldAlert size={12} />
                    <span>{riskEvidence.length}</span>
                    {showHallazgos ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                  </button>
                )}
                <button
                  onClick={() => {
                    setEditingId(risk.id);
                    setExpandedHallazgos(new Set());
                    setEditForm({ probability: risk.probability, impact: risk.impact, rationale: risk.likelihood_rationale ?? "", priority: risk.priority ?? "medium_term" });
                  }}
                  className="text-xs text-blue-600 hover:text-blue-800 px-2.5 py-1 rounded-lg hover:bg-blue-50 transition-colors">
                  Editar
                </button>
                <button
                  onClick={() => { if (confirm("¿Eliminar este riesgo?")) deleteMutation.mutate(risk.id); }}
                  disabled={deleteMutation.isPending}
                  className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 hover:bg-red-50 px-2.5 py-1 rounded-lg transition-colors">
                  <Trash2 size={13} />
                  Eliminar
                </button>
              </div>
            )}
          </div>
        )}


        {/* Hallazgos expandible */}
        {showHallazgos && !isEditing && riskEvidence.length > 0 && (
          <div className="px-5 pb-4 pt-3 border-t border-orange-100 bg-orange-50/30 space-y-2">
            <p className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 uppercase tracking-wide">
              <ShieldAlert size={13} className="text-orange-400" />
              Hallazgos vinculados — {riskEvidence.length}
            </p>
            <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
              {riskEvidence.map((f: any) => (
                <div key={f.id} className="flex items-start gap-2.5 bg-white border border-gray-200 rounded-lg px-3 py-2.5">
                  <span className={cn("text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0 mt-0.5", SEV_BADGE[f.severity] ?? SEV_BADGE.info)}>
                    {f.severity}
                  </span>
                  {scannerBadge(f.scanner)}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-800">{f.title}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {[f.category, f.cwe ? `CWE-${f.cwe}` : null, f.owasp_category, f.asset_name].filter(Boolean).join(" · ")}
                    </p>
                    {f.file_path && (
                      <p className="text-xs text-gray-400 font-mono mt-0.5 truncate">
                        {f.file_path}{f.line_start ? `:${f.line_start}` : ""}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Edit panel */}
        {isEditing && (
          <div className="px-5 pb-5 pt-2 border-t border-blue-100 bg-blue-50/30 space-y-5">

            {/* 4 dimensiones de impacto en el panel de edición */}
            {(risk.impact_operational || risk.impact_financial || risk.impact_normative || risk.impact_reputational) && (
              <div className="grid grid-cols-4 gap-3 bg-white border border-gray-200 rounded-lg p-3">
                {[
                  { label: "Operacional",   value: risk.impact_operational },
                  { label: "Financiero",    value: risk.impact_financial },
                  { label: "Normativo",     value: risk.impact_normative },
                  { label: "Reputacional",  value: risk.impact_reputational },
                ].map(({ label, value }) => (
                  <div key={label} className="text-center">
                    <p className="text-xs text-gray-500 font-medium mb-1">{label}</p>
                    {value ? (
                      <span className={cn("text-xs font-bold px-2 py-0.5 rounded border", IMPACT_COLOR[value] ?? "text-gray-500 bg-gray-50 border-gray-200")}>
                        {value}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-300">N/A</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Sliders P × I */}
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-2">
                  Probabilidad — <span className="text-blue-600">{editForm.probability}</span>/5
                </label>
                <input type="range" min={1} max={5} step={1}
                  value={editForm.probability}
                  onChange={e => setEditForm(f => ({ ...f, probability: Number(e.target.value) }))}
                  className="w-full accent-blue-600" />
                <div className="flex justify-between text-xs text-gray-300 mt-0.5"><span>Muy baja</span><span>Muy alta</span></div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-2">
                  Impacto — <span className="text-blue-600">{editForm.impact}</span>/5
                </label>
                <input type="range" min={1} max={5} step={1}
                  value={editForm.impact}
                  onChange={e => setEditForm(f => ({ ...f, impact: Number(e.target.value) }))}
                  className="w-full accent-blue-600" />
                <div className="flex justify-between text-xs text-gray-300 mt-0.5"><span>Muy bajo</span><span>Muy alto</span></div>
              </div>
            </div>

            <div className="w-1/2">
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Prioridad recomendada</label>
              <select value={editForm.priority} onChange={e => setEditForm(f => ({ ...f, priority: e.target.value }))}
                className="w-full bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                {Object.entries(PRIORITY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>

            {(risk.risk_description || risk.business_impact_desc) && (
              <div className="bg-white border border-blue-200 shadow-sm rounded-lg p-4 space-y-3">
                {risk.risk_description && (
                  <div>
                    <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
                      <AlertTriangle size={13} className="text-yellow-500" /> Escenario de Riesgo
                    </h4>
                    <p className="text-sm text-gray-600 mt-1.5 leading-relaxed">{risk.risk_description}</p>
                  </div>
                )}
                {risk.business_impact_desc && (
                  <div className={risk.risk_description ? "pt-3 border-t border-gray-100" : ""}>
                    <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
                      <BarChart3 size={13} className="text-blue-500" /> Impacto en el Negocio
                    </h4>
                    <p className="text-sm text-gray-600 mt-1.5 leading-relaxed">{risk.business_impact_desc}</p>
                  </div>
                )}
              </div>
            )}

            {riskEvidence.length > 0 && (
              <div className="space-y-2">
                <p className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  <ShieldAlert size={13} className="text-gray-400" />
                  Evidencia técnica — {riskEvidence.length} hallazgo{riskEvidence.length !== 1 ? "s" : ""} vinculado{riskEvidence.length !== 1 ? "s" : ""}
                </p>
                <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                  {riskEvidence.map((f: any) => (
                    <div key={f.id} className="flex items-start gap-2.5 bg-white border border-gray-200 rounded-lg px-3 py-2">
                      <span className={cn("text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0 mt-0.5", SEV_BADGE[f.severity] ?? SEV_BADGE.info)}>
                        {f.severity}
                      </span>
                      {scannerBadge(f.scanner)}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 truncate">{f.title}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {f.category}{f.cwe ? ` · CWE-${f.cwe}` : ""}
                          {f.file_path ? ` · ${f.file_path}${f.line_start ? `:${f.line_start}` : ""}` : ""}
                        </p>
                      </div>
                      {f.owasp_category && <span className="text-xs text-gray-400 flex-shrink-0 font-mono">{f.owasp_category}</span>}
                    </div>
                  ))}
                </div>
                {riskEvidence.length > 1 && (
                  <p className="text-xs text-blue-600 font-medium">
                    Cobertura: {riskEvidence.filter((f: any) => f.severity === "critical").length} críticos ·{" "}
                    {riskEvidence.filter((f: any) => f.severity === "high").length} altos
                  </p>
                )}
              </div>
            )}

            {snippetLoading ? (
              <div className="text-xs text-gray-500 py-3 text-center">
                <Loader size={14} className="animate-spin inline mr-1" /> Cargando fragmento de código…
              </div>
            ) : snippetData?.snippet?.length > 0 ? (
              <div className="space-y-2">
                <label className="flex items-center gap-1.5 text-xs font-semibold text-gray-600">
                  <Code size={13} /> Fragmento de código vulnerable (hallazgo principal)
                </label>
                <div className="bg-gray-900 rounded-lg overflow-hidden text-xs text-gray-300 font-mono overflow-x-auto">
                  {snippetData.snippet.map((line: any, i: number) => (
                    <div key={i} className={cn("px-3 py-0.5 whitespace-pre",
                      line.line === snippetData.finding?.line_start
                        ? "bg-red-900/40 text-red-100 border-l-2 border-red-500"
                        : "hover:bg-gray-800")}>
                      <span className="inline-block w-8 text-gray-600 select-none">{line.line}</span>
                      {line.code}
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => {
                    const codeStr = snippetData.snippet.map((l: any) => `${l.line}: ${l.code}`).join("\n");
                    const f = snippetData.finding || {};
                    const prompt = `Actúa como experto en ciberseguridad. Corrige esta vulnerabilidad:\n\nTítulo: ${f.title}\nArchivo: ${f.file_path}\n\nCódigo:\n\`\`\`\n${codeStr}\n\`\`\`\n\n¿Qué cambios exactos debo aplicar?`;
                    navigator.clipboard.writeText(prompt).then(() => showToast("Prompt de remediación copiado"));
                  }}
                  className="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium py-2 rounded-lg transition-colors"
                >
                  <Copy size={14} /> Copiar Prompt de Remediación
                </button>
              </div>
            ) : null}

            <div>
              <label className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 mb-1.5">
                <MessageSquare size={11} /> Justificación del CISO
              </label>
              <textarea
                value={editForm.rationale}
                onChange={e => setEditForm(f => ({ ...f, rationale: e.target.value }))}
                rows={2}
                placeholder="¿Por qué ajustaste estos valores? Ej: controles existentes reducen la probabilidad…"
                className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="text-sm">
                <span className="text-gray-500">Nuevo score: </span>
                <strong className="text-gray-900">{editForm.probability * editForm.impact}</strong>
                {(() => {
                  const s = editForm.probability * editForm.impact;
                  const level = s >= 20 ? "Crítico" : s >= 12 ? "Alto" : s >= 6 ? "Medio" : "Bajo";
                  const cls = s >= 20 ? "text-red-600" : s >= 12 ? "text-orange-500" : s >= 6 ? "text-yellow-600" : "text-green-600";
                  return <span className={cn("ml-2 text-xs font-bold", cls)}>({level})</span>;
                })()}
              </div>
              <button
                onClick={() => updateMutation.mutate({ id: risk.id })}
                disabled={updateMutation.isPending}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2">
                {updateMutation.isPending
                  ? <><Loader size={13} className="animate-spin" /> Guardando…</>
                  : <><Save size={13} /> Guardar valoración</>}
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 bg-gray-900 text-white text-sm px-4 py-3 rounded-xl shadow-lg flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2">
          <CheckSquare size={15} className="text-green-400" />
          {toast}
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-blue-600 mb-1">{project?.name}</p>
          <h1 className="text-2xl font-bold text-gray-900">Análisis de Riesgos</h1>
          <p className="text-sm text-gray-500 mt-0.5">Valoración de probabilidad e impacto según ISO 31000.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (project?.id) {
                const token = localStorage.getItem("access_token");
                const url = `http://127.0.0.1:8000/api/v1/risks/projects/${project.id}/export`;
                
                fetch(url, { headers: { "Authorization": `Bearer ${token}` } })
                  .then(async res => {
                    if (!res.ok) {
                      console.error("Export error", await res.text());
                      return;
                    }
                    return res.blob();
                  })
                  .then(blob => {
                    if (!blob) return;
                    const a = document.createElement("a");
                    a.href = window.URL.createObjectURL(blob);
                    a.download = `Registro_Riesgos_${project.name}.xlsx`;
                    a.click();
                  });
              }
            }}
            className="flex items-center gap-2 text-sm font-medium rounded-xl px-4 py-2.5 bg-white text-gray-600 border border-gray-200 hover:border-green-300 hover:text-green-600 transition-all"
          >
            <Download size={15} />
            Exportar Excel
          </button>
          <button
            onClick={() => { setMergeMode(m => !m); setSelectedMerge(new Set()); }}
            className={cn(
              "flex items-center gap-2 text-sm font-medium rounded-xl px-4 py-2.5 transition-all border",
              mergeMode
                ? "bg-emerald-600 text-white border-emerald-600"
                : "bg-white text-gray-600 border-gray-200 hover:border-emerald-300 hover:text-emerald-600"
            )}
          >
            <GitMerge size={15} />
            {mergeMode ? "Cancelar fusión" : "Fusionar riesgos"}
          </button>
        </div>
      </div>

      {/* Merge banner */}
      {mergeMode && (
        <div className="flex items-center justify-between bg-purple-50 border border-purple-200 rounded-xl px-5 py-3">
          <p className="text-sm text-purple-700 font-medium">
            {selectedMerge.size < 2
              ? `Selecciona al menos 2 riesgos para fusionar (${selectedMerge.size} seleccionados)`
              : `${selectedMerge.size} riesgos seleccionados`}
          </p>
          <button
            onClick={() => mergeMutation.mutate(Array.from(selectedMerge))}
            disabled={selectedMerge.size < 2 || mergeMutation.isPending}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            {mergeMutation.isPending ? <><Loader size={13} className="animate-spin" /> Fusionando…</> : <><GitMerge size={13} /> Fusionar</>}
          </button>
        </div>
      )}

      {/* Summary pills */}
      <div className="flex items-center gap-3">
        {[["critical","Crítico"],["high","Alto"],["medium","Medio"],["low","Bajo"]].map(([level, label]) => (
          <div key={level} className={cn("flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium", LEVEL_TEXT[level])}>
            <span>{label}</span>
            <span className="font-bold">{summary[level] ?? 0}</span>
          </div>
        ))}
        <div className="ml-auto text-xs text-gray-400">
          Total: <strong className="text-gray-700">{summary.total ?? 0}</strong>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-6">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={cn("pb-3 text-sm font-medium border-b-2 transition-colors",
                tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-800")}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* TAB: Mapa de riesgo */}
      {tab === "Mapa de riesgo" && (
        <div className="bg-white border border-gray-200 rounded-2xl p-8">
          <RiskHeatmap
            risks={risks}
            riskConfig={riskConfig}
            onRiskClick={(id) => {
              const r = risks.find((x: any) => x.id === id);
              if (r) {
                setTab("Generar fichas RN-xxx");
                setEditingId(r.id);
                setEditForm({ probability: r.probability, impact: r.impact, rationale: r.likelihood_rationale ?? "", priority: r.priority ?? "medium_term" });
                setTimeout(() => {
                  document.getElementById(`risk-${r.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
                }, 80);
              }
            }}
          />
        </div>
      )}

      {/* TAB: Generar fichas RN-xxx */}
      {tab === "Generar fichas RN-xxx" && (() => {
        const withBoth = (scenariosData ?? []).filter((s: any) => s.probability != null && s.impact != null);
        const pending   = withBoth.filter((s: any) => s.status !== "risk_generated");
        const generated = withBoth.filter((s: any) => s.status === "risk_generated").length;
        const currentProviderObj = availableProviders.find(p => p.value === aiProvider);

        return (
          <div className="grid grid-cols-[1fr_320px] gap-6 items-start">

            {/* ── IZQUIERDA: fichas RN-xxx generadas ── */}
            <div className="space-y-4 min-w-0">
              {isLoading ? (
                <div className="text-gray-400 text-sm py-12 text-center">Cargando riesgos…</div>
              ) : risks.length === 0 ? (
                <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-12 text-center">
                  <BarChart3 size={32} className="mx-auto mb-3 text-gray-300" />
                  <p className="text-gray-400 text-sm font-medium">Sin fichas de riesgo generadas aún</p>
                  <p className="text-gray-300 text-xs mt-1">Usa el panel de la derecha para generar fichas RN-xxx.</p>
                </div>
              ) : grouped.map(({ process, risks: groupRisks }) => (
                <div key={process?.id ?? "unlinked"} className="space-y-2">
                  <div className="flex items-center gap-3 px-1">
                    <Layers size={15} className="text-gray-400 flex-shrink-0" />
                    {process ? (
                      <>
                        <span className="text-sm font-semibold text-gray-800">{process.name}</span>
                        <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full border", CRIT_COLOR[process.criticality])}>
                          {CRIT_LABEL[process.criticality] ?? process.criticality}
                        </span>
                        {process.revenue_dependency && (
                          <span className="text-[10px] text-gray-400 border border-gray-200 px-2 py-0.5 rounded-full">
                            Dep. ingresos: {process.revenue_dependency}
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-sm font-semibold text-gray-500">Sin proceso asignado</span>
                    )}
                    <span className="ml-auto text-xs text-gray-400">{groupRisks.length} riesgo{groupRisks.length !== 1 ? "s" : ""}</span>
                  </div>
                  <div className="space-y-2 pl-6 border-l-2 border-gray-100">
                    {groupRisks.map(risk => <RiskCard key={risk.id} risk={risk} />)}
                  </div>
                </div>
              ))}
            </div>

            {/* ── DERECHA: selector IA + tabla de escenarios ── */}
            <div className="space-y-4 sticky top-6">
              {withBoth.length === 0 ? (
                <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-4">
                  <Zap size={15} className="text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">Sin escenarios con P×I</p>
                    <p className="text-xs text-amber-600 mt-0.5">Evalúa probabilidad e impacto primero.</p>
                  </div>
                </div>
              ) : (
                <>
                  {/* Panel IA */}
                  <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <Brain size={15} className="text-indigo-600" />
                      <h3 className="text-sm font-semibold text-gray-800">Generar con IA</h3>
                    </div>

                    {availableProviders.length > 0 ? (
                      <>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">Proveedor de IA</label>
                          <select
                            value={aiProvider}
                            onChange={e => {
                              const next = e.target.value;
                              setAiProvider(next);
                              const p = availableProviders.find(p => p.value === next);
                              if (p && p.models.length > 0) setAiModel(p.models[0]);
                            }}
                            className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                          >
                            {availableProviders.map(p => (
                              <option key={p.value} value={p.value}>{p.label}</option>
                            ))}
                          </select>
                        </div>
                        {currentProviderObj && currentProviderObj.models.length > 0 && (
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Modelo</label>
                            <select
                              value={aiModel}
                              onChange={e => setAiModel(e.target.value)}
                              className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                            >
                              {currentProviderObj.models.map(m => (
                                <option key={m} value={m}>{m}</option>
                              ))}
                            </select>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
                        <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                        <span>Configura una clave API en Configuración.</span>
                      </div>
                    )}

                    <div className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
                      <span className="font-semibold text-gray-700">{withBoth.length} escenarios listos</span>
                      {generated > 0 && <span className="text-gray-400 ml-1">· {generated} convertidos</span>}
                    </div>

                    {generateFromScenariosMut.status === "error" && (
                      <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
                        <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                        <span>{(generateFromScenariosMut.error as any)?.response?.data?.detail ?? "Error al generar fichas."}</span>
                      </div>
                    )}

                    <button
                      onClick={() => generateFromScenariosMut.mutate()}
                      disabled={generateFromScenariosMut.isPending || pending.length === 0}
                      className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2.5 transition-all"
                    >
                      {generateFromScenariosMut.isPending
                        ? <><Loader size={13} className="animate-spin" /> Generando…</>
                        : <><Zap size={13} /> Generar fichas RN-xxx</>
                      }
                    </button>

                    <button
                      onClick={() => aplicarCatalogoMut.mutate()}
                      disabled={aplicarCatalogoMut.isPending || (risks?.length ?? 0) === 0}
                      title="Renombra todos los RN-xxx al lenguaje del Directorio usando el Catálogo Maestro (sin IA)"
                      className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2.5 transition-all"
                    >
                      {aplicarCatalogoMut.isPending
                        ? <><Loader size={13} className="animate-spin" /> Aplicando catálogo…</>
                        : <><BookOpen size={13} /> Aplicar Catálogo Maestro</>
                      }
                    </button>

                  </div>

                  {/* Tabla de escenarios */}
                  <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 space-y-2">
                    <p className="text-xs font-semibold text-indigo-900">Escenarios a convertir</p>
                    <div className="overflow-hidden border border-indigo-200 rounded-lg bg-white">
                      <table className="w-full text-xs">
                        <thead className="bg-indigo-50/60 border-b border-indigo-100">
                          <tr>
                            <th className="text-left px-3 py-2 font-semibold text-indigo-700">SC-xxx</th>
                            <th className="text-center px-2 py-2 font-semibold text-indigo-700">P</th>
                            <th className="text-center px-2 py-2 font-semibold text-indigo-700">I</th>
                            <th className="text-center px-2 py-2 font-semibold text-indigo-700">Estado</th>
                          </tr>
                        </thead>
                        <tbody>
                          {withBoth.map((s: any) => {
                            const score = (s.probability ?? 0) * (s.impact ?? 0);
                            const lvl = score >= 20 ? "critical" : score >= 12 ? "high" : score >= 6 ? "medium" : "low";
                            const lvlClass: Record<string,string> = { critical: "text-red-600", high: "text-orange-500", medium: "text-yellow-600", low: "text-green-600" };
                            return (
                              <tr key={s.id} className="border-b border-gray-100 last:border-0">
                                <td className="px-3 py-2">
                                  <span className="font-mono text-indigo-600">{s.scenario_code ?? "SC-?"}</span>
                                </td>
                                <td className="px-2 py-2 text-center font-bold text-gray-700">{s.probability}</td>
                                <td className="px-2 py-2 text-center font-bold text-gray-700">{s.impact}</td>
                                <td className="px-2 py-2 text-center">
                                  {s.status === "risk_generated"
                                    ? <span className="inline-block w-2 h-2 rounded-full bg-green-500" title="Generado" />
                                    : <span className={cn("font-bold text-[10px]", lvlClass[lvl])}>{score}</span>
                                  }
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </div>

          </div>
        );
      })()}

      {tab === "Criterios de Riesgo" && <RiskCriteriaTab section="levels" />}

    </div>
  );
}
