"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scanSessionsApi, codeSourcesApi, assetsApi, scannersApi, workspacesApi } from "@/lib/api";
import { biaApi } from "@/lib/api/context";
import { useProjectStore } from "@/lib/project";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import { Play, Clock, CheckCircle, XCircle, Loader, Server, RefreshCw, ChevronDown, ChevronRight, Trash2, StopCircle, ShieldAlert, Download } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type ConfirmState = { title: string; desc: string; action?: string; onConfirm: () => void } | null;


const STATUS_ICON: Record<string, React.ReactNode> = {
  pending:   <Clock size={13} className="text-gray-400" />,
  running:   <Loader size={13} className="text-blue-500 animate-spin" />,
  completed: <CheckCircle size={13} className="text-green-500" />,
  failed:    <XCircle size={13} className="text-red-500" />,
  cancelled: <XCircle size={13} className="text-gray-400" />,
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente", running: "En curso",
  completed: "Completado", failed: "Fallido", cancelled: "Cancelado",
};

export default function ScansPage() {
  const qc = useQueryClient();
  const { project, assetId, setAssetId } = useProjectStore();
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [selectedScanners, setSelectedScanners] = useState<string[]>([]);
  const [isRetest, setIsRetest] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedAiProvider, setSelectedAiProvider] = useState<string>("");
  const [selectedMobsfType, setSelectedMobsfType] = useState<string>("apk");
  const [customHeaders, setCustomHeaders] = useState<string>("");
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const askConfirm = (c: NonNullable<ConfirmState>) => setConfirm(c);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExportVuln = async () => {
    if (!project?.id) return;
    setExporting(true);
    setExportError(null);
    try {
      await biaApi.exportVulnExcel(project.id, project.name);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Error al exportar");
    } finally {
      setExporting(false);
    }
  };

  const [scannerHealth, setScannerHealth] = useState<Record<string, "ok" | "error" | "checking">>({
    sonarqube: "checking",
    zap: "checking",
    mobsf: "checking",
  });
  const [installedScanners, setInstalledScanners] = useState<string[]>([]);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  useEffect(() => {
    // Legacy check for backward compatibility or backend health
    const checkScanners = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000), cache: "no-store" });
        const data = await res.json().catch(() => null);
        const installed = data?.installed_scanners || ["sonarqube", "zap", "mobsf"];
        setInstalledScanners(installed);
      } catch {
        setInstalledScanners(["sonarqube", "zap", "mobsf"]);
      }
    };
    checkScanners();
  }, []);

  const { data: activeScannersData, isLoading: isLoadingScanners } = useQuery({
    queryKey: ["scanners"],
    queryFn: () => scannersApi.list().then(res => res.data),
  });

  const activeScanners = activeScannersData?.filter((s: any) => s.is_active) || [];

  const { data: workspaceData } = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: () => workspacesApi.getSettings().then(res => res.data),
  });

  const enabledProviders = workspaceData?.ai_config?.providers
    ? Object.entries(workspaceData.ai_config.providers)
        .filter(([_, prov]: [string, any]) => prov.enabled)
        .map(([name]) => name)
    : [];

  useEffect(() => {
    if (enabledProviders.length > 0 && !selectedAiProvider) {
      setSelectedAiProvider(enabledProviders[0]);
    }
  }, [enabledProviders, selectedAiProvider]);

  const { data: sourcesData } = useQuery({
    queryKey: ["code-sources", project?.id],
    queryFn: () => codeSourcesApi.list(project!.id).then((r) => r.data),
    enabled: !!project,
  });

  const { data: assetsData } = useQuery({
    queryKey: ["assets", project?.id],
    queryFn: () => assetsApi.list(project!.id, { size: 50 }).then((r: any) => r.data),
    enabled: !!project,
  });

  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ["scan-sessions", project?.id, assetId],
    queryFn: () => scanSessionsApi.list(project!.id, { 
      size: 50,
      asset_id: assetId !== "all" ? assetId : undefined
    }).then((r) => r.data),
    refetchInterval: 8000,
    enabled: !!project,
  });

  const { data: expandedScans } = useQuery({
    queryKey: ["session-scans", expandedId],
    queryFn: () => scanSessionsApi.listScans(expandedId!).then((r) => r.data),
    enabled: !!expandedId,
    refetchInterval: 8000,
  });

  const triggerMutation = useMutation({
    mutationFn: () => {
      const parsedHeaders = customHeaders.split('\n').map(h => h.trim()).filter(Boolean);
      return scanSessionsApi.create(project!.id, {
        code_source_id: selectedSourceId || undefined,
        asset_id: (!selectedSourceId && assetId !== "all") ? assetId : undefined,
        scanners: selectedScanners,
        scanner_configs: {
          ...(selectedScanners.includes("ai_review") ? { ai_review: { ai_provider: selectedAiProvider } } : {}),
          ...(selectedScanners.includes("mobsf") ? { mobsf: { scan_type: selectedMobsfType } } : {}),
          ...(selectedScanners.includes("nuclei") && parsedHeaders.length > 0 ? { nuclei: { custom_headers: parsedHeaders } } : {}),
          ...(selectedScanners.includes("zap") && parsedHeaders.length > 0 ? { zap: { custom_headers: parsedHeaders } } : {}),
        },
        is_retest: isRetest,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scan-sessions"] });
      setSelectedSourceId("");
      setIsRetest(false);
    },
  });

  const cancelSessionMutation = useMutation({
    mutationFn: (sessionId: string) => scanSessionsApi.cancel(sessionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scan-sessions"] }),
  });

  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => scanSessionsApi.delete(sessionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scan-sessions"] }),
  });

  const sources = (sourcesData ?? [])
    .filter((s: any) => s.status === "ready")
    .filter((s: any) => assetId === "all" ? true : s.asset_id === assetId);
  const sessions = sessionsData?.items ?? [];
  const activeAsset = assetId !== "all" ? assetsData?.items?.find((a: any) => a.id === assetId) : null;
  const isScannable = true;

  return (
    <div className="space-y-6">
      {confirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-gray-900 mb-2">{confirm.title}</h3>
            <p className="text-sm text-gray-500 mb-5">{confirm.desc}</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirm(null)}
                className="px-4 py-2 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">
                Cancelar
              </button>
              <button onClick={() => { confirm.onConfirm(); setConfirm(null); }}
                className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors">
                {confirm.action ?? "Eliminar"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="mb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium text-blue-600 mb-1">{project?.name}</p>
            <h1 className="text-2xl font-bold text-gray-900">Identificación de hallazgos</h1>
            <p className="text-sm text-gray-500 mt-0.5">Ejecución de escáneres sobre snapshots de código</p>
          </div>
          {project?.id && (
            <button
              onClick={handleExportVuln}
              disabled={exporting}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg transition-colors shadow-sm whitespace-nowrap"
            >
              {exporting ? <Loader size={15} className="animate-spin" /> : <Download size={15} />}
              {exporting ? "Exportando…" : "Exportar Excel"}
            </button>
          )}
        </div>
        {exportError && (
          <p className="mt-2 text-xs text-red-600">{exportError}</p>
        )}
      </div>

      {/* Layout de dos columnas: Configuración a la izquierda, Tabla a la derecha */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        
        {/* Columna Izquierda: Configuración */}
        <div className="w-full lg:w-[280px] flex-shrink-0">
          {!isScannable ? (
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-5 text-center shadow-sm">
              <ShieldAlert size={24} className="mx-auto mb-2 text-blue-500" />
              <h2 className="text-sm font-semibold text-blue-900 mb-1">Escaneo no requerido</h2>
              <p className="text-xs text-blue-700 mx-auto mb-4">El tipo de activo "{activeAsset?.asset_type}" no admite escaneos automáticos de código. Las vulnerabilidades deben registrarse manualmente.</p>
              <Link href="/identificacion" className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg px-4 py-2 transition-colors shadow-sm w-full justify-center">
                Ir a Vulnerabilidades
              </Link>
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm sticky top-6">
              <h2 className="text-sm font-semibold text-gray-800 mb-4">Configurar escaneo</h2>
              <div className="flex flex-col gap-5">
                
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-2">1. Selecciona el activo</label>
                  <select
                    value={assetId}
                    onChange={(e) => {
                      setAssetId(e.target.value);
                      setSelectedSourceId(""); // Reset source when asset changes
                    }}
                    className="w-full bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
                  >
                    <option value="all">Todos los activos</option>
                    {assetsData?.items?.map((a: any) => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-2">2. Selecciona la fuente</label>
                  {sources.length > 0 ? (
                    <select
                      value={selectedSourceId}
                      onChange={(e) => setSelectedSourceId(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
                    >
                      <option value="">Seleccionar fuente…</option>
                      {sources.map((s: any) => (
                        <option key={s.id} value={s.id}>{s.label}</option>
                      ))}
                    </select>
                  ) : (
                    <div className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-400">
                      {assetId === "all" ? "Sin fuentes de código" : "Este activo no tiene fuentes de código"}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-2">3. Motores de análisis</label>
                  <div className="flex flex-col gap-3">
                    {isLoadingScanners ? (
                      <div className="text-xs text-gray-500 flex items-center gap-2"><Loader size={14} className="animate-spin" /> Cargando motores...</div>
                    ) : activeScanners.length === 0 ? (
                      <div className="text-xs text-gray-500">No hay escáneres activos. Regístralos en Monitoreo.</div>
                    ) : (
                      Object.entries(
                        activeScanners.reduce((acc: any, scanner: any) => {
                          const cat = scanner.category || 'otros';
                          if (!acc[cat]) acc[cat] = [];
                          acc[cat].push(scanner);
                          return acc;
                        }, {})
                      ).map(([category, catScanners]: [string, any]) => (
                        <div key={category} className="mb-2">
                          <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 px-1">
                            {category === 'sast' ? 'SAST (Análisis Estático)' :
                             category === 'dast' ? 'DAST (Análisis Dinámico)' :
                             category === 'sca' ? 'SCA (Dependencias)' :
                             category === 'ia' ? 'Revisión IA' :
                             category === 'vuln' ? 'Gestión de Vulnerabilidades' :
                             category}
                          </h3>
                          <div className="flex flex-col gap-2">
                            {catScanners.map((scanner: any) => {
                              const isChecked = selectedScanners.includes(scanner.engine_type);
                              
                              return (
                                <div key={scanner.id} className={cn("flex flex-col rounded-lg transition-colors border", 
                                  isChecked ? "bg-blue-50 border-blue-300" : "bg-gray-50 border-gray-200 hover:border-gray-300"
                                )}>
                                  <label className="flex items-center gap-2 text-xs font-medium px-3 py-3 cursor-pointer w-full h-full">
                                    <input type="checkbox" checked={isChecked} onChange={(e) => {
                                      setSelectedScanners(prev => e.target.checked ? [...prev, scanner.engine_type] : prev.filter(s => s !== scanner.engine_type));
                                    }} className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                                    <span className={isChecked ? "text-blue-800" : "text-gray-700"}>{scanner.name}</span>
                                  </label>
                                  
                                  {scanner.engine_type === "ai_review" && isChecked && enabledProviders.length > 0 && (
                                    <div className="px-3 pb-3 pt-0">
                                      <div className="flex flex-col gap-1.5 bg-white p-2 rounded border border-blue-100">
                                        <span className="text-[10px] text-blue-600 font-semibold uppercase tracking-wider">Proveedor de IA</span>
                                        <select
                                          value={selectedAiProvider}
                                          onChange={(e) => setSelectedAiProvider(e.target.value)}
                                          className="text-xs bg-transparent text-gray-700 focus:outline-none w-full cursor-pointer"
                                        >
                                          {enabledProviders.map((providerName: string) => (
                                            <option key={providerName} value={providerName}>
                                              {providerName === "anthropic" ? "Anthropic" : providerName === "gemini" ? "Google Gemini" : providerName === "openai" ? "OpenAI" : "Ollama (Local)"}
                                            </option>
                                          ))}
                                        </select>
                                      </div>
                                    </div>
                                  )}

                                  {scanner.engine_type === "mobsf" && isChecked && (
                                    <div className="px-3 pb-3 pt-0">
                                      <div className="flex flex-col gap-1.5 bg-white p-2 rounded border border-blue-100">
                                        <span className="text-[10px] text-blue-600 font-semibold uppercase tracking-wider">Tipo de Análisis</span>
                                        <select
                                          value={selectedMobsfType}
                                          onChange={(e) => setSelectedMobsfType(e.target.value)}
                                          className="text-xs bg-transparent text-gray-700 focus:outline-none w-full cursor-pointer"
                                        >
                                          <option value="apk">APK (Android)</option>
                                          <option value="ipa">IPA (iOS)</option>
                                          <option value="zip">Automático (ZIP/Auto)</option>
                                        </select>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ))
                    )}
                    {selectedScanners.includes("ai_review") && enabledProviders.length === 0 && (
                      <div className="mt-1 text-xs text-amber-600 bg-amber-50 p-2 rounded border border-amber-200">
                        Se usará Ollama (Local) por defecto.
                      </div>
                    )}
                  </div>
                </div>

                {(selectedScanners.includes("nuclei") || selectedScanners.includes("zap")) && (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-2">Opciones Avanzadas</label>
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                      <label className="block text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Cabeceras Personalizadas (Opcional)</label>
                      <textarea 
                        value={customHeaders}
                        onChange={(e) => setCustomHeaders(e.target.value)}
                        placeholder="Cookie: PHPSESSID=123456789&#10;Authorization: Bearer token..."
                        className="w-full bg-white border border-gray-200 text-gray-700 text-xs rounded-md px-3 py-2 h-20 resize-none focus:outline-none focus:border-blue-500 transition-colors placeholder:text-gray-400"
                      />
                      <p className="text-[10px] text-gray-400 mt-1.5 leading-snug">
                        Agrega una cabecera por línea para realizar escaneos autenticados en DAST.
                      </p>
                    </div>
                  </div>
                )}

                <div className="pt-4 border-t border-gray-100 flex flex-col gap-2.5">
                  <label className={cn("flex items-center justify-center gap-2 text-xs font-medium rounded-lg px-3 py-2 cursor-pointer transition-colors border", isRetest ? "bg-blue-50 border-blue-300 text-blue-700" : "bg-gray-50 border-gray-200 text-gray-700 hover:border-gray-300")}>
                    <input type="checkbox" checked={isRetest} onChange={(e) => setIsRetest(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600" />
                    <RefreshCw size={14} className={isRetest ? "text-blue-500" : "text-gray-500"} /> Forzar Retest
                  </label>

                  <button
                    onClick={() => triggerMutation.mutate()}
                    disabled={
                      (selectedScanners.some(s => !['zap', 'nuclei', 'openvas'].includes(s)) && !selectedSourceId) ||
                      (!selectedSourceId && assetId === "all") ||
                      selectedScanners.length === 0 ||
                      triggerMutation.isPending
                    }
                    className="flex items-center justify-center w-full gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl px-4 py-2.5 transition-colors"
                  >
                    <Play size={14} />
                    {triggerMutation.isPending ? "Iniciando…" : "Ejecutar análisis"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Columna Derecha: Listado de Escaneos */}
        <div className="flex-1 min-w-0">
          <div className="bg-white border border-gray-200 rounded-xl overflow-x-auto shadow-sm">
            <table className="w-full text-sm min-w-[800px]">
              <thead className="border-b border-gray-200 bg-gray-50">
            <tr className="text-xs text-gray-400 uppercase tracking-wide">
              <th className="w-8 p-4" />
              <th className="text-left p-4">Sesión</th>
              <th className="text-left p-4">Fuente</th>
              <th className="text-left p-4">Estado</th>
              <th className="text-left p-4">Hallazgos</th>
              <th className="text-left p-4">Nuevos</th>
              <th className="text-left p-4">Tipo</th>
              <th className="text-left p-4">Iniciado</th>
              <th className="p-4" />
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="p-8 text-center text-gray-400">Cargando sesiones…</td></tr>
            ) : sessions.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-12 text-center">
                  <Server size={28} className="mx-auto mb-3 text-gray-300" />
                  <p className="text-gray-400 text-sm">Sin análisis registrados para este proyecto.</p>
                </td>
              </tr>
            ) : (
              sessions.map((session: any) => (
                <>
                  <tr
                    key={session.id}
                    className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                    onClick={() => setExpandedId(expandedId === session.id ? null : session.id)}
                  >
                    <td className="p-4 text-gray-400">
                      {expandedId === session.id
                        ? <ChevronDown size={14} />
                        : <ChevronRight size={14} />}
                    </td>
                    <td className="p-4 font-mono text-xs text-gray-400">{session.id.slice(0, 8)}…</td>
                    <td className="p-4 text-xs text-gray-600">{session.code_source_id?.slice(0, 8) ?? "—"}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {STATUS_ICON[session.status]}
                        <span className={cn("text-xs font-medium", {
                          "text-green-600": session.status === "completed",
                          "text-red-500": session.status === "failed",
                          "text-blue-600": session.status === "running",
                          "text-gray-500": session.status === "pending" || session.status === "cancelled",
                        })}>
                          {STATUS_LABELS[session.status] ?? session.status}
                        </span>
                      </div>
                    </td>
                    <td className="p-4 text-gray-800 font-semibold">{session.total_findings_count ?? 0}</td>
                    <td className="p-4 text-green-600 font-semibold">
                      {(session.new_findings_count ?? 0) > 0 ? `+${session.new_findings_count}` : "—"}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {session.is_retest
                          ? <span className="text-xs bg-purple-50 text-purple-600 px-2 py-0.5 rounded border border-purple-200">Retest</span>
                          : <span className="text-xs bg-gray-50 text-gray-500 px-2 py-0.5 rounded border">Inicial</span>}
                      </div>
                    </td>
                    <td className="p-4 text-xs text-gray-500">
                      {session.created_at ? format(new Date(session.created_at), "d MMM, HH:mm") : "—"}
                    </td>
                    <td className="p-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-3">
                        {(session.status === "running" || session.status === "pending") && (
                          <button
                            onClick={() => askConfirm({
                              title: "¿Detener escaneo?",
                              desc: "La sesión se marcará como cancelada. El proceso puede tardar unos segundos en detenerse.",
                              action: "Detener",
                              onConfirm: () => cancelSessionMutation.mutate(session.id),
                            })}
                            className="text-amber-500 hover:text-amber-700 transition-colors" title="Detener escaneo">
                            <StopCircle size={15} />
                          </button>
                        )}
                        <button
                          onClick={() => askConfirm({
                            title: "¿Eliminar sesión?",
                            desc: "Se eliminarán todos los hallazgos asociados a esta sesión. Esta acción no se puede deshacer.",
                            onConfirm: () => deleteSessionMutation.mutate(session.id),
                          })}
                          className="text-gray-300 hover:text-red-500 transition-colors" title="Eliminar sesión">
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                  
                  {/* Progress Bar Row */}
                  {session.status === "running" && (
                    <tr>
                      <td colSpan={9} className="p-0">
                        <div className="w-full h-1 bg-gray-100 overflow-hidden relative">
                          <div className="absolute top-0 left-0 h-full bg-blue-500 w-1/2 animate-[progress_2s_ease-in-out_infinite]" />
                        </div>
                      </td>
                    </tr>
                  )}

                  {expandedId === session.id && (
                    <tr key={`${session.id}-detail`} className="bg-gray-50 border-t border-gray-100">
                      <td colSpan={9} className="px-8 py-4">
                        <div className="space-y-1.5">
                          {!expandedScans ? (
                            <p className="text-xs text-gray-400">Cargando escáneres…</p>
                          ) : expandedScans.length === 0 ? (
                            <p className="text-xs text-gray-400">Sin escáneres en esta sesión.</p>
                          ) : expandedScans.map((scan: any) => (
                            <div key={scan.id} className="flex items-center gap-4 text-xs bg-white rounded-lg border border-gray-200 px-4 py-2">
                              <span className="font-mono text-gray-400">{scan.id.slice(0, 8)}…</span>
                              <span className="bg-gray-100 text-gray-600 rounded px-2 py-0.5">{scan.scanner_type}</span>
                              <div className="flex items-center gap-1.5">
                                {STATUS_ICON[scan.status]}
                                <span className="text-gray-600">{STATUS_LABELS[scan.status] ?? scan.status}</span>
                              </div>
                              <span className="text-gray-500">{scan.findings_count ?? 0} hallazgos</span>
                              {scan.error_message && (
                                <span className="text-red-500 truncate max-w-xs">{scan.error_message}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>
        </div>
      </div>
    </div>
  );
}
