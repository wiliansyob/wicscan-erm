"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { findingsApi, scanSessionsApi, workspacesApi } from "@/lib/api";
import { scenariosApi, type ConsolidateResult } from "@/lib/api/assessment";
import { useProjectStore } from "@/lib/project";
import {
  Target, Loader, ChevronDown, AlertTriangle, Code, Copy,
  Plus, X, Brain, Sparkles, CheckCircle2, ArrowRight, RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import Link from "next/link";

const SEV_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:      "bg-blue-100 text-blue-700 border-blue-200",
  info:     "bg-gray-100 text-gray-500 border-gray-200",
};

const DEFAULT_AI_PROVIDERS = [
  { value: "anthropic", label: "Anthropic Claude" },
  { value: "gemini",    label: "Google Gemini" },
  { value: "ollama",    label: "Ollama (local)" },
];

export default function IdentificacionPage() {
  const qc = useQueryClient();
  const { project, assetId } = useProjectStore();

  // ── Filters / pagination ──────────────────────────────────────────────────
  const [sessionFilter, setSessionFilter]     = useState("");
  const [scannerFilter, setScannerFilter]     = useState("");
  const [severityFilter, setSeverityFilter]   = useState<string[]>([]);
  const [sevDropdownOpen, setSevDropdownOpen] = useState(false);
  const [page, setPage]                       = useState(1);

  // ── Selection ─────────────────────────────────────────────────────────────
  const [selectedFindings, setSelectedFindings] = useState<Set<string>>(new Set());

  // ── Code snippet expand ───────────────────────────────────────────────────
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);

  // ── AI provider / model ───────────────────────────────────────────────────
  const [aiProvider, setAiProvider] = useState("anthropic");
  const [aiModel, setAiModel]       = useState("");

  // ── Result state ──────────────────────────────────────────────────────────
  const [consolidateResult, setConsolidateResult] = useState<ConsolidateResult | null>(null);

  // ── Manual form ───────────────────────────────────────────────────────────
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualFormData, setManualFormData] = useState({
    title: "", description: "", severity: "medium", category: "manual_review", cwe: "",
  });

  // ── Queries ───────────────────────────────────────────────────────────────
  const { data: workspaceSettings } = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: () => workspacesApi.getSettings().then(r => r.data),
    enabled: !!project,
  });

  const { data: sessionsData } = useQuery({
    queryKey: ["scan-sessions", project?.id, assetId],
    queryFn: () => scanSessionsApi.list(project!.id, {
      size: 20,
      asset_id: assetId !== "all" ? assetId : undefined,
    }).then(r => r.data),
    enabled: !!project,
  });

  const { data: findingsData, isLoading: loadingFindings } = useQuery({
    queryKey: ["findings-ident", project?.id, assetId, sessionFilter, severityFilter, scannerFilter, page],
    queryFn: () => findingsApi.list({
      project_id: project?.id,
      asset_id: assetId !== "all" ? assetId : undefined,
      status: "open",
      scan_session_id: sessionFilter || undefined,
      severity: severityFilter.length > 0 ? severityFilter : undefined,
      scanner: scannerFilter || undefined,
      page,
      size: 10,
    }).then(r => r.data),
    enabled: !!project,
  });

  const { data: snippetData, isLoading: snippetLoading } = useQuery({
    queryKey: ["finding-snippet", expandedFinding],
    queryFn: () => expandedFinding ? findingsApi.getSnippet(expandedFinding).then(r => r.data) : null,
    enabled: !!expandedFinding,
  });

  // ── Available AI providers from workspace settings ────────────────────────
  const availableProviders: { value: string; label: string; models: string[] }[] = (() => {
    const config = workspaceSettings?.ai_config;
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
          if (match) list.push({ ...match, models: parseModels(prov.model, key === "anthropic" ? "claude-3-5-sonnet-20241022" : "gemini-flash-latest") });
        }
      });
      return list;
    }
    DEFAULT_AI_PROVIDERS.forEach(p => {
      if (config[`${p.value}_api_key`]) list.push({ ...p, models: ["Default"] });
    });
    return list;
  })();

  useEffect(() => {
    if (availableProviders.length > 0) {
      const current = availableProviders.find(p => p.value === aiProvider) ?? availableProviders[0];
      if (!availableProviders.find(p => p.value === aiProvider)) setAiProvider(current.value);
      if (current.models.length > 0 && !current.models.includes(aiModel)) setAiModel(current.models[0]);
    }
  }, [workspaceSettings]);

  // ── Mutations ─────────────────────────────────────────────────────────────
  const consolidateMut = useMutation<ConsolidateResult, Error, void>({
    mutationFn: () => {
      const ids: string[] | undefined = selectedFindings.size > 0 ? [...selectedFindings] : undefined;
      return scenariosApi.consolidar(project!.id, ids).then(r => r.data as ConsolidateResult);
    },
    onSuccess: (data: ConsolidateResult) => {
      setConsolidateResult(data);
      setSelectedFindings(new Set());
      qc.invalidateQueries({ queryKey: ["scenarios"] });
    },
  });

  const createManualMutation = useMutation({
    mutationFn: (data: any) => findingsApi.createManual(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings-ident"] });
      setShowManualForm(false);
      setManualFormData({ title: "", description: "", severity: "medium", category: "manual_review", cwe: "" });
    },
  });

  // ── Helpers ───────────────────────────────────────────────────────────────
  const completedSessions = (sessionsData?.items ?? []).filter((s: any) => s.status === "completed");
  const findings: any[] = findingsData?.items ?? [];

  const toggleFinding = (id: string) =>
    setSelectedFindings(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const toggleAll = async () => {
    if (selectedFindings.size > 0) { setSelectedFindings(new Set()); return; }
    const res = await findingsApi.list({
      project_id: project?.id,
      asset_id: assetId !== "all" ? assetId : undefined,
      status: "open",
      scan_session_id: sessionFilter || undefined,
      severity: severityFilter.length > 0 ? severityFilter : undefined,
      scanner: scannerFilter || undefined,
      size: 5000,
    });
    setSelectedFindings(new Set(res.data.items.map((f: any) => f.id)));
  };

  const toggleSeverity = (sev: string) => {
    setSeverityFilter(prev => { const n = prev.includes(sev) ? prev.filter(s => s !== sev) : [...prev, sev]; setPage(1); return n; });
  };

  const currentProvider = availableProviders.find(p => p.value === aiProvider);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium text-blue-600 mb-1">{project?.name}</p>
        <h1 className="text-2xl font-bold text-gray-900">Registro de hallazgos</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Selecciona hallazgos y usa la IA para agruparlos en escenarios de riesgo. Los escenarios pasan a calificarse en Probabilidad e Impacto.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* ── LEFT: hallazgos ─────────────────────────────────────────────── */}
        <div className="col-span-2 space-y-4">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {findingsData?.total > 0 && (
                  <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-2.5 py-0.5 font-medium">
                    {findingsData.total} hallazgos
                  </span>
                )}
                <button onClick={() => setShowManualForm(true)}
                  className="bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-200 text-xs font-medium px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors">
                  <Plus size={14} /> Nuevo Hallazgo Manual
                </button>
              </div>
              {findingsData?.total > 0 && (
                <button onClick={toggleAll} className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                  {selectedFindings.size > 0 ? `${selectedFindings.size} seleccionados · Deseleccionar` : "Seleccionar todo"}
                </button>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <button onClick={() => setSevDropdownOpen(!sevDropdownOpen)}
                  className="flex items-center gap-2 bg-white border border-gray-200 text-gray-600 text-xs rounded-lg px-3 py-1.5">
                  {severityFilter.length === 0 ? "Todas las severidades" : `${severityFilter.length} severidades`}
                  <ChevronDown size={14} />
                </button>
                {sevDropdownOpen && (
                  <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1">
                    {["critical", "high", "medium", "low", "info"].map(sev => (
                      <label key={sev} className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 cursor-pointer">
                        <input type="checkbox" checked={severityFilter.includes(sev)} onChange={() => toggleSeverity(sev)}
                          className="rounded border-gray-300 text-blue-600" />
                        <span className="text-xs text-gray-700 capitalize">{sev}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
              {completedSessions.length > 0 && (
                <select value={sessionFilter} onChange={e => { setSessionFilter(e.target.value); setPage(1); }}
                  className="bg-white border border-gray-200 text-gray-600 text-xs rounded-lg px-3 py-1.5">
                  <option value="">Todas las sesiones</option>
                  {completedSessions.map((s: any) => (
                    <option key={s.id} value={s.id}>{format(new Date(s.created_at), "dd MMM, HH:mm")}</option>
                  ))}
                </select>
              )}
              <select value={scannerFilter} onChange={e => { setScannerFilter(e.target.value); setPage(1); }}
                className="bg-white border border-gray-200 text-gray-600 text-xs rounded-lg px-3 py-1.5">
                <option value="">Todos los análisis</option>
                <option value="sonarqube">SAST (SonarQube)</option>
                <option value="zap">DAST (OWASP ZAP)</option>
              </select>
            </div>
          </div>

          {loadingFindings ? (
            <div className="text-gray-400 text-sm py-8 text-center">Cargando hallazgos…</div>
          ) : findings.length === 0 ? (
            <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-10 text-center">
              <Target size={28} className="mx-auto mb-3 text-gray-300" />
              <p className="text-gray-500 text-sm font-medium">Sin hallazgos abiertos</p>
              <p className="text-gray-400 text-xs mt-1">Ejecuta un escaneo desde la sección Identificación.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-1.5">
                {findings.map((f: any) => (
                  <div key={f.id} className={cn(
                    "bg-white border rounded-xl overflow-hidden transition-all",
                    selectedFindings.has(f.id) ? "border-blue-400 bg-blue-50/40" : "border-gray-200 hover:border-gray-300"
                  )}>
                    <div className="flex items-start gap-3 px-4 py-3">
                      <input type="checkbox" checked={selectedFindings.has(f.id)} onChange={() => toggleFinding(f.id)}
                        className="mt-0.5 rounded border-gray-300 text-blue-600 flex-shrink-0 cursor-pointer" />
                      <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setExpandedFinding(expandedFinding === f.id ? null : f.id)}>
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className={cn("text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0", SEV_STYLES[f.severity] ?? SEV_STYLES.info)}>
                            {f.severity}
                          </span>
                          {(f.scanner === "sonarqube" || f.scanner === "zap") && (
                            <span className={cn(
                              "text-[10px] uppercase font-mono px-1.5 rounded border",
                              f.scanner === "sonarqube" ? "bg-indigo-50 text-indigo-700 border-indigo-200" : "bg-emerald-50 text-emerald-700 border-emerald-200"
                            )}>
                              {f.scanner === "sonarqube" ? "SAST" : "DAST"}
                            </span>
                          )}
                          <p className="text-sm font-medium text-gray-900 truncate">{f.title}</p>
                        </div>
                        <p className="text-xs text-gray-400 flex items-center justify-between">
                          <span>{f.category}{f.cwe ? ` · CWE-${f.cwe}` : ""}{f.file_path ? ` · ${f.file_path}${f.line_start ? `:${f.line_start}` : ""}` : ""}</span>
                          {f.file_path && f.line_start && (
                            <span className="text-blue-600 flex items-center gap-1 hover:underline">
                              <Code size={12} /> {expandedFinding === f.id ? "Ocultar código" : "Ver código"}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>

                    {expandedFinding === f.id && (
                      <div className="px-4 pb-4 pt-1 border-t border-gray-100 bg-gray-50">
                        {snippetLoading ? (
                          <div className="text-xs text-gray-500 py-4 text-center"><Loader size={14} className="animate-spin inline mr-1" />Cargando fragmento...</div>
                        ) : snippetData?.snippet?.length > 0 ? (
                          <div className="space-y-3 mt-2">
                            <div className="bg-gray-900 rounded-lg overflow-hidden text-xs text-gray-300 font-mono overflow-x-auto">
                              {snippetData.snippet.map((line: any, i: number) => (
                                <div key={i} className={cn("px-3 py-0.5 whitespace-pre",
                                  line.line === f.line_start ? "bg-red-900/40 text-red-100 border-l-2 border-red-500" : "hover:bg-gray-800")}>
                                  <span className="inline-block w-8 text-gray-600 select-none">{line.line}</span>
                                  {line.code}
                                </div>
                              ))}
                            </div>
                            <button onClick={() => {
                              const codeStr = snippetData.snippet.map((l: any) => `${l.line}: ${l.code}`).join("\n");
                              const prompt = `Actúa como un experto en ciberseguridad. Por favor, ayúdame a corregir la siguiente vulnerabilidad:\n\nTítulo: ${f.title}\nDescripción: ${f.description || "N/A"}\nArchivo: ${f.file_path}\n\nCódigo:\n\`\`\`\n${codeStr}\n\`\`\`\n\n¿Qué cambios aplicar para solucionar la vulnerabilidad?`;
                              navigator.clipboard.writeText(prompt);
                              alert("¡Prompt copiado al portapapeles!");
                            }} className="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium py-2 rounded-lg transition-colors">
                              <Copy size={14} /> Copiar Prompt de Remediación
                            </button>
                          </div>
                        ) : (
                          <div className="text-xs text-gray-500 py-4 text-center">No se pudo obtener el código fuente.</div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {findingsData?.pages > 1 && (
                <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-4 py-3">
                  <p className="text-xs text-gray-500">
                    Mostrando {(page - 1) * 10 + 1}–{Math.min(page * 10, findingsData.total)} de {findingsData.total}
                  </p>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                      className="text-xs font-medium text-gray-600 bg-gray-50 border border-gray-200 hover:bg-gray-100 disabled:opacity-50 rounded px-3 py-1.5">
                      Anterior
                    </button>
                    <span className="text-xs text-gray-600 font-medium px-2">Página {page} de {findingsData.pages}</span>
                    <button onClick={() => setPage(p => Math.min(findingsData.pages, p + 1))} disabled={page === findingsData.pages}
                      className="text-xs font-medium text-gray-600 bg-gray-50 border border-gray-200 hover:bg-gray-100 disabled:opacity-50 rounded px-3 py-1.5">
                      Siguiente
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── RIGHT: agente IA ─────────────────────────────────────────────── */}
        <div className="space-y-4">
          {consolidateResult ? (
            /* ── Result card ── */
            <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-green-600" />
                <h3 className="text-sm font-semibold text-gray-800">Consolidación completada</h3>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-green-50 rounded-lg p-3 text-center border border-green-100">
                  <p className="text-2xl font-bold text-green-700">{consolidateResult.scenarios_created}</p>
                  <p className="text-gray-500 mt-0.5">Escenarios creados</p>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center border border-blue-100">
                  <p className="text-2xl font-bold text-blue-700">{consolidateResult.findings_processed}</p>
                  <p className="text-gray-500 mt-0.5">Hallazgos agrupados</p>
                </div>
              </div>
              <Link href="/probabilidad"
                className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl py-2.5 transition-all">
                Calificar probabilidad <ArrowRight size={14} />
              </Link>
              <button onClick={() => { setConsolidateResult(null); consolidateMut.reset(); }}
                className="flex items-center justify-center gap-1.5 w-full text-xs text-gray-500 hover:text-gray-700">
                <RefreshCw size={11} /> Volver a consolidar
              </button>
            </div>
          ) : (
            /* ── AI panel ── */
            <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
              <div className="flex items-center gap-2">
                <Brain size={16} className="text-purple-600" />
                <h3 className="text-sm font-semibold text-gray-800">Agente IA</h3>
              </div>

              {availableProviders.length > 0 ? (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Proveedor de IA</label>
                    <select value={aiProvider} onChange={e => setAiProvider(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500">
                      {availableProviders.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                    </select>
                  </div>

                  {currentProvider && currentProvider.models.length > 0 && (
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1.5">Modelo a usar</label>
                      <select value={aiModel} onChange={e => setAiModel(e.target.value)}
                        className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500">
                        {currentProvider.models.map(m => <option key={m} value={m}>{m}</option>)}
                      </select>
                    </div>
                  )}

                  {availableProviders.length === 1 && (
                    <p className="text-[10px] text-gray-400">
                      Configura más claves API en Configuración para usar otros motores.
                    </p>
                  )}
                </>
              ) : (
                <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
                  <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
                  <span>Configura una clave API en Configuración para usar la IA.</span>
                </div>
              )}

              <div className="bg-purple-50 rounded-lg p-3 text-xs text-purple-800 space-y-1">
                <p className="font-semibold">El agente IA:</p>
                <p>• Agrupa hallazgos por vector de ataque (SC-xxx)</p>
                <p>• Evalúa la probabilidad de cada escenario (1-5)</p>
                <p>• Los escenarios pasan a Probabilidad e Impacto</p>
              </div>

              {consolidateMut.error && (
                <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
                  <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
                  <span>Error al consolidar. Inténtalo de nuevo.</span>
                </div>
              )}

              <button
                onClick={() => consolidateMut.mutate()}
                disabled={!project || consolidateMut.isPending || (findingsData?.total ?? 0) === 0}
                className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2.5 transition-all">
                {consolidateMut.isPending
                  ? <><Loader size={14} className="animate-spin" /> Agrupando…</>
                  : <><Sparkles size={14} /> Analizar con IA</>}
              </button>

              <p className="text-xs text-gray-400 text-center">
                {selectedFindings.size > 0
                  ? `${selectedFindings.size} hallazgos seleccionados`
                  : "Se analizarán todos los hallazgos"}
              </p>
            </div>
          )}

          {/* Flujo de evaluación */}
          {!consolidateResult && (
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Flujo de evaluación</p>
              {[
                { step: "1", label: "Analizar con IA", href: "/identificacion", active: true },
                { step: "2", label: "Calificar probabilidad", href: "/probabilidad", active: false },
                { step: "3", label: "Calificar impacto", href: "/impacto", active: false },
                { step: "4", label: "Generar análisis", href: "/analisis", active: false },
              ].map(({ step, label, href, active }) => (
                <Link key={step} href={href} className={cn(
                  "flex items-center gap-3 p-2 rounded-lg text-xs transition-colors",
                  active ? "bg-purple-50 text-purple-700 font-semibold" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                )}>
                  <span className={cn(
                    "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0",
                    active ? "bg-purple-600 text-white" : "bg-gray-200 text-gray-500"
                  )}>{step}</span>
                  {label}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Manual Entry Modal */}
      {showManualForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Ingreso Manual de Hallazgo</h2>
              <button onClick={() => setShowManualForm(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Título *</label>
                <input type="text" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={manualFormData.title} onChange={e => setManualFormData({ ...manualFormData, title: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Descripción</label>
                <textarea className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
                  value={manualFormData.description} onChange={e => setManualFormData({ ...manualFormData, description: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Severidad *</label>
                  <select className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    value={manualFormData.severity} onChange={e => setManualFormData({ ...manualFormData, severity: e.target.value })}>
                    <option value="critical">Crítico</option>
                    <option value="high">Alto</option>
                    <option value="medium">Medio</option>
                    <option value="low">Bajo</option>
                    <option value="info">Info</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Categoría</label>
                  <input type="text" placeholder="Ej: pentest, config…" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    value={manualFormData.category} onChange={e => setManualFormData({ ...manualFormData, category: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">CWE (Opcional)</label>
                <input type="text" placeholder="Ej: CWE-79" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                  value={manualFormData.cwe} onChange={e => setManualFormData({ ...manualFormData, cwe: e.target.value })} />
              </div>
            </div>
            {assetId === "all" && (
              <div className="px-5 pb-2 text-xs text-red-500 font-medium">
                Selecciona una aplicación específica en el selector superior.
              </div>
            )}
            <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
              <button onClick={() => setShowManualForm(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg">Cancelar</button>
              <button
                disabled={!manualFormData.title || !assetId || assetId === "all" || createManualMutation.isPending}
                onClick={() => createManualMutation.mutate({ ...manualFormData, asset_id: assetId })}
                className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg font-medium flex items-center gap-2">
                {createManualMutation.isPending ? "Guardando..." : "Guardar Hallazgo"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
