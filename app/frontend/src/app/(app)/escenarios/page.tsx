"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { findingsApi, scanSessionsApi, workspacesApi } from "@/lib/api";
import { scenariosApi, type RiskScenarioOut } from "@/lib/api/assessment";
import { biaApi } from "@/lib/api/context";
import { useProjectStore } from "@/lib/project";
import {
  Target, Loader, ChevronDown, AlertTriangle, Code, Copy,
  Plus, X, Brain, Sparkles, CheckCircle2, ArrowRight, RefreshCw,
  List, BookOpen, Upload, FileText, Edit2, Trash2, Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import Link from "next/link";
import { RiskCriteriaTab } from "@/components/risks/risk-criteria";

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

const TABS = ["Hallazgos", "Criterios de P e I"] as const;
type Tab = typeof TABS[number];

// ─── Hallazgos + IA tab ───────────────────────────────────────────────────────

function HallazgosTab() {
  const qc = useQueryClient();
  const { project, assetId } = useProjectStore();

  const [sessionFilter, setSessionFilter]     = useState("");
  const [scannerFilter, setScannerFilter]     = useState("");
  const [severityFilter, setSeverityFilter]   = useState<string[]>([]);
  const [statusFilter, setStatusFilter]       = useState("open");
  const [sevDropdownOpen, setSevDropdownOpen] = useState(false);
  const [page, setPage]                       = useState(1);
  const [selectedFindings, setSelectedFindings] = useState<Set<string>>(new Set());
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);
  const [aiProvider, setAiProvider] = useState("anthropic");
  const [aiModel, setAiModel]       = useState("");
  const [analyzeResult, setAnalyzeResult] = useState<RiskScenarioOut[] | null>(null);
  const [analyzeStep, setAnalyzeStep] = useState<"idle" | "analyzing" | "done" | "error">("idle");
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualFormData, setManualFormData] = useState({
    title: "", description: "", severity: "medium", category: "manual_review", cwe: "", source: "",
  });
  const [showCsvForm, setShowCsvForm] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [uploadingCsv, setUploadingCsv] = useState(false);

  const [showEditForm, setShowEditForm] = useState(false);
  const [editingFindingId, setEditingFindingId] = useState<string | null>(null);
  const [editFormData, setEditFormData] = useState({
    title: "", description: "", severity: "medium", category: "", cwe: "", source: "", status: "open", asset_id: ""
  });

  const { data: assetsData } = useQuery({
    queryKey: ["assets-for-findings", project?.id],
    queryFn: () => biaApi.listAssets(project!.id).then((r: { data: { items: { id: string; name: string; asset_type: string }[] } }) => r.data),
    enabled: !!project && showEditForm,
  });
  const assetsList = assetsData?.items ?? [];

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingFindingId, setDeletingFindingId] = useState<string | null>(null);

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
    queryKey: ["findings-escenarios", project?.id, assetId, sessionFilter, severityFilter, scannerFilter, statusFilter, page],
    queryFn: () => findingsApi.list({
      project_id: project?.id,
      asset_id: assetId !== "all" ? assetId : undefined,
      status: statusFilter === "all" ? undefined : statusFilter,
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

  const { data: sourcesData } = useQuery({
    queryKey: ["findings-sources", project?.id, assetId],
    queryFn: () => findingsApi.sources({
      project_id: project?.id,
      asset_id: assetId !== "all" ? assetId : undefined,
      status: statusFilter === "all" ? undefined : statusFilter,
    }).then(r => r.data),
    enabled: !!project,
  });

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

  const handleAnalyze = async () => {
    if (!project) return;
    setAnalyzeStep("analyzing");
    setAnalyzeError(null);
    setAnalyzeResult(null);
    try {
      const ids = selectedFindings.size > 0 ? Array.from(selectedFindings) : undefined;
      const result = await scenariosApi.analizar(project.id, ids, aiProvider, aiModel).then(r => r.data);
      setAnalyzeResult(result);
      setSelectedFindings(new Set());
      qc.invalidateQueries({ queryKey: ["scenarios", project.id] });
      setAnalyzeStep("done");
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? err?.message ?? "Error desconocido";
      setAnalyzeError(msg);
      setAnalyzeStep("error");
    }
  };

  const createManualMutation = useMutation({
    mutationFn: (data: any) => findingsApi.createManual(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings-escenarios"] });
      setShowManualForm(false);
      setManualFormData({ title: "", description: "", severity: "medium", category: "manual_review", cwe: "", source: "" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: { id: string, payload: any }) => findingsApi.update(data.id, data.payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings-escenarios"] });
      setShowEditForm(false);
      setEditingFindingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => findingsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings-escenarios"] });
      setShowDeleteConfirm(false);
      setDeletingFindingId(null);
    },
  });

  const isAnalyzing = analyzeStep === "analyzing";
  const completedSessions = (sessionsData?.items ?? []).filter((s: any) => s.status === "completed");
  const findings: any[] = findingsData?.items ?? [];

  const toggleFinding = (id: string) =>
    setSelectedFindings(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const toggleAll = async () => {
    if (selectedFindings.size > 0) { setSelectedFindings(new Set()); return; }
    const res = await findingsApi.list({
      project_id: project?.id,
      asset_id: assetId !== "all" ? assetId : undefined,
      status: statusFilter === "all" ? undefined : statusFilter,
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
    <div className="grid grid-cols-3 gap-6">
      {/* LEFT: hallazgos */}
      <div className="col-span-2 space-y-4">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {findingsData?.total > 0 && (
                <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-2.5 py-0.5 font-medium">
                  {findingsData.total} hallazgos
                </span>
              )}
              <button onClick={() => setShowCsvForm(true)}
                className="bg-green-50 text-green-600 hover:bg-green-100 border border-green-200 text-xs font-medium px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors">
                <Upload size={14} /> Cargar CSV
              </button>
              <button onClick={() => setShowManualForm(true)}
                className="bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-200 text-xs font-medium px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors">
                <Plus size={14} /> Nuevo hallazgo manual
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
                <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-xl shadow-lg z-10 py-1">
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
              {sourcesData?.map((source: string) => (
                <option key={source} value={source}>
                  {source === "sonarqube" ? "SAST (SonarQube)" : source === "zap" ? "DAST (OWASP ZAP)" : source === "manual" ? "Manual" : source}
                </option>
              ))}
            </select>
            <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
              className="bg-white border border-gray-200 text-gray-600 text-xs rounded-lg px-3 py-1.5">
              <option value="all">Todos los estados</option>
              <option value="open">Abierto (Verdadero Positivo)</option>
              <option value="confirmed">Confirmado</option>
              <option value="false_positive">Falso Positivo</option>
              <option value="resolved">Resuelto</option>
            </select>
          </div>
        </div>

        {loadingFindings ? (
          <div className="text-gray-400 text-sm py-8 text-center">Cargando hallazgos…</div>
        ) : findings.length === 0 ? (
          <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-10 text-center">
            <Target size={28} className="mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500 text-sm font-medium">Sin hallazgos abiertos</p>
            <p className="text-gray-400 text-xs mt-1">Ejecuta un escaneo desde Identificación.</p>
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
                        {f.scanner && (
                          <span className={cn(
                            "text-[10px] uppercase font-mono px-1.5 rounded border",
                            f.scanner === "sonarqube" || f.scanner.toLowerCase().includes("sast") 
                              ? "bg-indigo-50 text-indigo-700 border-indigo-200" 
                              : f.scanner === "zap" || f.scanner.toLowerCase().includes("dast") 
                                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                : "bg-gray-100 text-gray-700 border-gray-200"
                          )}>
                            {f.scanner === "sonarqube" ? "SAST" : f.scanner === "zap" ? "DAST" : f.scanner === "manual" ? "MANUAL" : f.scanner}
                          </span>
                        )}
                        <p className="text-sm font-medium text-gray-900 truncate">{f.title}</p>
                      </div>
                      <p className="text-xs text-gray-400 flex items-center justify-between">
                        <span className="flex-1">{f.category}{f.cwe ? ` · CWE-${f.cwe}` : ""}{f.file_path ? ` · ${f.file_path}${f.line_start ? `:${f.line_start}` : ""}` : ""}</span>
                        <span className="flex items-center gap-3">
                          {f.file_path && f.line_start && (
                            <span className="text-blue-600 flex items-center gap-1 hover:underline">
                              <Code size={12} /> {expandedFinding === f.id ? "Ocultar" : "Código"}
                            </span>
                          )}
                          <div className="flex items-center gap-2">
                            <button onClick={(e) => { e.stopPropagation(); setEditingFindingId(f.id); setEditFormData({ title: f.title, description: f.description || "", severity: f.severity, category: f.category, cwe: f.cwe || "", source: f.scanner || "", status: f.status, asset_id: f.asset_id || "" }); setShowEditForm(true); }} className="text-gray-400 hover:text-blue-600">
                              <Edit2 size={13} />
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); setDeletingFindingId(f.id); setShowDeleteConfirm(true); }} className="text-gray-400 hover:text-red-600">
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </span>
                      </p>
                    </div>
                  </div>

                  {expandedFinding === f.id && (
                    <div className="px-4 pb-4 pt-3 border-t border-gray-100 bg-gray-50">
                      {f.description && (
                        <div className="mb-4 text-sm text-gray-700 whitespace-pre-wrap">
                          <span className="font-semibold text-gray-900 block mb-1">Descripción:</span>
                          {f.description}
                        </div>
                      )}
                      {f.remediation_guidance && (
                        <div className="mb-4 text-sm text-gray-700 whitespace-pre-wrap">
                          <span className="font-semibold text-gray-900 block mb-1">Recomendación:</span>
                          {f.remediation_guidance}
                        </div>
                      )}
                      
                      {snippetLoading ? (
                        <div className="text-xs text-gray-500 py-4 text-center"><Loader size={14} className="animate-spin inline mr-1" />Cargando fragmento...</div>
                      ) : snippetData?.snippet?.length > 0 ? (
                        <div className="space-y-3 mt-2">
                          <h4 className="text-xs font-semibold text-gray-900">Fragmento de código vulnerable</h4>
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
                            const prompt = `Actúa como un experto en ciberseguridad. Ayúdame a corregir la siguiente vulnerabilidad:\n\nTítulo: ${f.title}\nDescripción: ${f.description || "N/A"}\nArchivo: ${f.file_path}\n\nCódigo:\n\`\`\`\n${codeStr}\n\`\`\`\n\n¿Qué cambios aplicar para solucionar la vulnerabilidad?`;
                            navigator.clipboard.writeText(prompt);
                          }} className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
                            <Copy size={12} /> Copiar prompt de IA
                          </button>
                        </div>
                      ) : null}
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

      {/* RIGHT: agente IA */}
      <div className="space-y-4">
        {/* ── AI Analysis Panel ── */}
        {analyzeStep === "done" ? (
          // ── Done state ──
          <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-green-600" />
              <h3 className="text-sm font-semibold text-gray-800">Análisis completado</h3>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-green-50 rounded-lg p-3 text-center border border-green-100">
                <p className="text-2xl font-bold text-green-700">{analyzeResult?.length ?? 0}</p>
                <p className="text-gray-500 mt-0.5">Escenarios</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-3 text-center border border-blue-100">
                <p className="text-2xl font-bold text-blue-700">
                  {analyzeResult?.filter(s => s.probability != null).length ?? 0}
                </p>
                <p className="text-gray-500 mt-0.5">Con probabilidad</p>
              </div>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-2 text-green-700">
                <CheckCircle2 size={13} /> IA agrupó hallazgos en escenarios SC-xxx
              </div>
              <div className="flex items-center gap-2 text-green-700">
                <CheckCircle2 size={13} /> IA asignó probabilidad y generó descripción
              </div>
            </div>
            <Link href="/probabilidad"
              className="flex items-center justify-center gap-2 w-full bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl py-2.5 transition-all">
              Ver probabilidad <ArrowRight size={14} />
            </Link>
            <button
              onClick={() => { setAnalyzeStep("idle"); setAnalyzeResult(null); setAnalyzeError(null); }}
              className="flex items-center justify-center gap-1.5 w-full text-xs text-gray-500 hover:text-gray-700"
            >
              <RefreshCw size={11} /> Volver a analizar
            </button>
          </div>
        ) : analyzeStep === "analyzing" ? (
          // ── In-progress state ──
          <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Loader size={16} className="text-purple-600 animate-spin" />
              <h3 className="text-sm font-semibold text-gray-800">IA analizando hallazgos…</h3>
            </div>
            <div className="flex items-center gap-3 text-xs bg-purple-50 border border-purple-100 text-purple-700 rounded-lg px-3 py-2.5">
              <Loader size={13} className="animate-spin flex-shrink-0" />
              <span className="font-medium">Agrupando y evaluando probabilidad en un solo paso…</span>
            </div>
            <p className="text-xs text-gray-400 text-center">Esto puede tardar 15-45 segundos</p>
          </div>
        ) : (
          // ── Idle / Error state ──
          <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Brain size={16} className="text-purple-600" />
              <h3 className="text-sm font-semibold text-gray-800">Analizar con IA</h3>
            </div>

            {availableProviders.length > 0 ? (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Proveedor de IA</label>
                  <select value={aiProvider} onChange={e => {
                      const next = e.target.value;
                      setAiProvider(next);
                      const p = availableProviders.find(p => p.value === next);
                      if (p && p.models.length > 0) setAiModel(p.models[0]);
                    }}
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500">
                    {availableProviders.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                  </select>
                </div>
                {currentProvider && currentProvider.models.length > 0 && (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Modelo</label>
                    <select value={aiModel} onChange={e => setAiModel(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500">
                      {currentProvider.models.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
                <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
                <span>Configura una clave API en Configuración para usar la IA.</span>
              </div>
            )}

            <div className="space-y-1.5 text-xs text-gray-500 bg-gray-50 rounded-lg p-3">
              <p className="font-semibold text-gray-700">La IA hace todo en un solo paso:</p>
              <p>① Agrupa hallazgos por vector de ataque en escenarios SC-xxx</p>
              <p>② Genera título y descripción ejecutiva de cada escenario</p>
              <p>③ Asigna probabilidad recomendada (1-5) con justificación</p>
            </div>

            {analyzeStep === "error" && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
                <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
                <span>{analyzeError ?? "Error al analizar."}</span>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!project || isAnalyzing || (findingsData?.total ?? 0) === 0}
              className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2.5 transition-all"
            >
              <Sparkles size={14} /> Analizar con IA
            </button>

            <p className="text-xs text-gray-400 text-center">
              {selectedFindings.size > 0
                ? `${selectedFindings.size} hallazgos seleccionados`
                : "Se analizarán todos los hallazgos"}
            </p>
          </div>
        )}

        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Flujo de evaluación</p>
          {[
            { step: "1", label: "Analizar con IA", href: "/escenarios", active: true },
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
                active ? "bg-emerald-600 text-white" : "bg-gray-200 text-gray-500"
              )}>{step}</span>
              {label}
            </Link>
          ))}
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
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">CWE (Opcional)</label>
                  <input type="text" placeholder="Ej: CWE-79" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    value={manualFormData.cwe} onChange={e => setManualFormData({ ...manualFormData, cwe: e.target.value })} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Fuente (Opcional)</label>
                  <input type="text" placeholder="Ej: Pentesting, SAST..." className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    value={manualFormData.source} onChange={e => setManualFormData({ ...manualFormData, source: e.target.value })} />
                </div>
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
                className="px-4 py-2 text-sm text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg font-medium flex items-center gap-2">
                {createManualMutation.isPending ? "Guardando..." : "Guardar hallazgo"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Carga CSV */}
      {showCsvForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">Carga Masiva de Hallazgos (CSV)</h2>
              <button onClick={() => { setShowCsvForm(false); setCsvFile(null); }} className="text-gray-400 hover:text-gray-600 transition-colors">
                <X size={20} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
                <p className="font-semibold mb-1">Formato CSV Esperado:</p>
                <p>El archivo debe incluir al menos las columnas <code>title</code> y <code>severity</code>. Otras columnas opcionales son: <code>description</code>, <code>category</code>, <code>finding_type</code>, <code>cwe</code>, <code>cvss_score</code>, <code>source</code>.</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-2">Archivo CSV *</label>
                <div className="relative">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                    className="block w-full text-sm text-gray-500
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-lg file:border-0
                      file:text-sm file:font-semibold
                      file:bg-green-50 file:text-green-700
                      hover:file:bg-green-100
                      border border-gray-200 rounded-lg cursor-pointer"
                  />
                </div>
              </div>

              {assetId === "all" && (
                <div className="text-xs text-red-500 font-medium">
                  Selecciona una aplicación específica en el selector superior de la página antes de cargar.
                </div>
              )}
            </div>
            <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
              <button onClick={() => { setShowCsvForm(false); setCsvFile(null); }} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg">Cancelar</button>
              <button
                disabled={!csvFile || assetId === "all" || uploadingCsv}
                onClick={async () => {
                  if (!csvFile || assetId === "all") return;
                  setUploadingCsv(true);
                  try {
                    await findingsApi.uploadCsv(assetId, csvFile);
                    qc.invalidateQueries({ queryKey: ["findings-escenarios"] });
                    setShowCsvForm(false);
                    setCsvFile(null);
                  } catch (e) {
                    console.error("Error uploading CSV", e);
                    alert("Error al cargar el archivo CSV. Verifica el formato.");
                  } finally {
                    setUploadingCsv(false);
                  }
                }}
                className="px-4 py-2 text-sm text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg font-medium flex items-center gap-2">
                {uploadingCsv ? (
                  <><RefreshCw size={14} className="animate-spin" /> Cargando...</>
                ) : (
                  <><FileText size={14} /> Cargar hallazgos</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Modal: Editar Hallazgo */}
      {showEditForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Editar Hallazgo</h2>
              <button onClick={() => setShowEditForm(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Título *</label>
                <input type="text" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={editFormData.title} onChange={e => setEditFormData({ ...editFormData, title: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Descripción</label>
                <textarea className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
                  value={editFormData.description} onChange={e => setEditFormData({ ...editFormData, description: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Severidad *</label>
                  <select className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    value={editFormData.severity} onChange={e => setEditFormData({ ...editFormData, severity: e.target.value })}>
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
                    value={editFormData.category} onChange={e => setEditFormData({ ...editFormData, category: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">CWE (Opcional)</label>
                  <input type="text" placeholder="Ej: CWE-79" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    value={editFormData.cwe} onChange={e => setEditFormData({ ...editFormData, cwe: e.target.value })} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Fuente/Scanner</label>
                  <input type="text" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                    value={editFormData.source} onChange={e => setEditFormData({ ...editFormData, source: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Estado</label>
                <select className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none"
                  value={editFormData.status} onChange={e => setEditFormData({ ...editFormData, status: e.target.value })}>
                  <option value="open">Abierto (Verdadero Positivo)</option>
                  <option value="confirmed">Confirmado</option>
                  <option value="false_positive">Falso Positivo</option>
                  <option value="resolved">Resuelto</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Activo afectado
                  <span className="ml-1 text-indigo-500 font-normal">(necesario para generar escenarios correctos)</span>
                </label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={editFormData.asset_id}
                  onChange={e => setEditFormData({ ...editFormData, asset_id: e.target.value })}
                >
                  <option value="">— Sin activo asignado —</option>
                  {assetsList.map((a) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.asset_type})</option>
                  ))}
                </select>
                {!editFormData.asset_id && (
                  <p className="text-xs text-amber-600 mt-1">
                    ⚠ Sin activo, este hallazgo no podrá vincularse a un proceso de negocio en los escenarios.
                  </p>
                )}
              </div>
            </div>
            <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
              <button onClick={() => setShowEditForm(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg">Cancelar</button>
              <button
                disabled={!editFormData.title || updateMutation.isPending}
                onClick={() => {
                  if (editingFindingId) {
                    updateMutation.mutate({
                      id: editingFindingId,
                      payload: {
                        title: editFormData.title,
                        description: editFormData.description,
                        severity: editFormData.severity,
                        category: editFormData.category,
                        cwe: editFormData.cwe,
                        scanner: editFormData.source,
                        status: editFormData.status,
                        ...(editFormData.asset_id ? { asset_id: editFormData.asset_id } : {}),
                      }
                    });
                  }
                }}
                className="px-4 py-2 text-sm text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg font-medium">
                {updateMutation.isPending ? "Guardando..." : "Guardar cambios"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Eliminar Hallazgo */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden flex flex-col">
            <div className="p-5 space-y-3">
              <div className="flex items-center gap-3 text-red-600">
                <AlertTriangle size={24} />
                <h2 className="text-lg font-semibold text-gray-900">Eliminar Hallazgo</h2>
              </div>
              <p className="text-sm text-gray-600">
                ¿Estás seguro de que deseas eliminar este hallazgo? Esta acción no se puede deshacer.
              </p>
            </div>
            <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
              <button onClick={() => setShowDeleteConfirm(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg font-medium">Cancelar</button>
              <button
                disabled={deleteMutation.isPending}
                onClick={() => {
                  if (deletingFindingId) deleteMutation.mutate(deletingFindingId);
                }}
                className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg font-medium">
                {deleteMutation.isPending ? "Eliminando..." : "Eliminar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EscenariosPage() {
  const { project } = useProjectStore();
  const [activeTab, setActiveTab] = useState<Tab>("Hallazgos");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportingRaw, setExportingRaw] = useState(false);
  const [exportRawError, setExportRawError] = useState<string | null>(null);

  const handleExport = async () => {
    if (!project?.id) return;
    setExporting(true);
    setExportError(null);
    try {
      await scenariosApi.exportExcel(project.id, project.name);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Error al exportar");
    } finally {
      setExporting(false);
    }
  };

  const handleExportRaw = async () => {
    if (!project?.id) return;
    setExportingRaw(true);
    setExportRawError(null);
    try {
      const res = await findingsApi.list({ project_id: project.id, size: 5000 });
      const rawData = res.data.items;
      const blob = new Blob([JSON.stringify(rawData, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `hallazgos_raw_${project.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportRawError(e instanceof Error ? e.message : "Error al descargar JSON");
    } finally {
      setExportingRaw(false);
    }
  };

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Selecciona un proyecto para continuar.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium text-blue-600 mb-1">{project.name}</p>
            <h1 className="text-2xl font-bold text-gray-900">Escenarios</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Selecciona hallazgos y usa la IA para agruparlos en escenarios SC-xxx. Luego califica probabilidad e impacto.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleExportRaw}
              disabled={exportingRaw}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 disabled:opacity-50 rounded-lg transition-colors shadow-sm whitespace-nowrap"
            >
              {exportingRaw ? <Loader size={15} className="animate-spin" /> : <Download size={15} />}
              {exportingRaw ? "Descargando…" : "Exportar JSON (Raw)"}
            </button>
            <button
              onClick={handleExport}
              disabled={exporting}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg transition-colors shadow-sm whitespace-nowrap"
            >
              {exporting ? <Loader size={15} className="animate-spin" /> : <Download size={15} />}
              {exporting ? "Exportando…" : "Exportar Excel"}
            </button>
          </div>
        </div>
        {(exportError || exportRawError) && (
          <p className="mt-2 text-xs text-red-600">{exportError || exportRawError}</p>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              activeTab === tab
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            )}
          >
            {tab === "Hallazgos" ? <List size={14} /> : <BookOpen size={14} />}
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Hallazgos" && <HallazgosTab />}
      {activeTab === "Criterios de P e I" && <RiskCriteriaTab section="pi" />}
    </div>
  );
}
