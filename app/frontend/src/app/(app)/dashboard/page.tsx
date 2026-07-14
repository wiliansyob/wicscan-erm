"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { risksApi, findingsApi, assetsApi, codeSourcesApi } from "@/lib/api";
import { useProjectStore } from "@/lib/project";
import {
  AlertTriangle, Shield, ShieldAlert, Activity,
  ChevronLeft, ChevronRight,
  Globe, Code, Layers, Server,
  AppWindow, Plus, Loader, FileText, Trash2, Circle, ArrowLeft, Edit2, Settings,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Asset meta ───────────────────────────────────────────────────
const TYPE_ICON: Record<string, React.ReactNode> = {
  web_app_scan: <Layers size={14} />,
  cybersecurity_audit: <FileText size={14} />,
  network_equipment: <Server size={14} />,
  security_reviews: <ShieldAlert size={14} />,
  threat_intelligence: <Globe size={14} />,
  other: <Code size={14} />,
};
const TYPE_LABELS: Record<string, string> = {
  web_app_scan: "Aplicación",
  cybersecurity_audit: "Auditoría de ciberseguridad",
  network_equipment: "Equipos de red",
  security_reviews: "Revisiones de seguridad",
  threat_intelligence: "Alertas de inteligencia de amenazas",
  other: "Otros",
};
const CRIT_STYLES: Record<string, string> = {
  critical: "text-red-600 bg-red-50 border-red-200",
  high:     "text-orange-600 bg-orange-50 border-orange-200",
  medium:   "text-yellow-600 bg-yellow-50 border-yellow-200",
  low:      "text-blue-600 bg-blue-50 border-blue-200",
};
const CRIT_LABELS: Record<string, string> = {
  critical: "Crítico", high: "Alto", medium: "Medio", low: "Bajo",
};
const SOURCE_STATUS: Record<string, { dot: string; label: string }> = {
  ready:   { dot: "bg-green-500",              label: "Listo" },
  cloning: { dot: "bg-blue-500 animate-pulse", label: "Clonando…" },
  pending: { dot: "bg-yellow-500",             label: "Pendiente" },
  error:   { dot: "bg-red-500",               label: "Error" },
};

// ─── Risk labels ─────────────────────────────────────────────────
const LEVEL_LABELS: Record<string, string> = {
  critical: "Crítico", high: "Alto", medium: "Medio", low: "Bajo",
};
const STATUS_LABELS: Record<string, string> = {
  open: "Abierto", in_progress: "En proceso", mitigated: "Mitigado", accepted: "Aceptado",
};
const LEVEL_COLOR: Record<string, string> = {
  critical: "text-red-600 bg-red-50 border-red-200",
  high:     "text-orange-600 bg-orange-50 border-orange-200",
  medium:   "text-yellow-700 bg-yellow-50 border-yellow-200",
  low:      "text-blue-600 bg-blue-50 border-blue-200",
};
const STATUS_COLOR: Record<string, string> = {
  open:        "text-gray-500 bg-gray-100",
  in_progress: "text-blue-600 bg-blue-50",
  mitigated:   "text-green-600 bg-green-50",
  accepted:    "text-purple-600 bg-purple-50",
};

const PAGE_SIZE = 10;

const BLANK_APP = {
  name: "", asset_type: "webapp", technical_owner: "",
};

type ConfirmState = { title: string; desc: string; onConfirm: () => void } | null;

// ─── Compact asset card (own source-status query) ─────────────────
function AssetCardCompact({ asset, projectId, isActive, onOpen, onEdit, onDelete }: {
  asset: any; projectId: string; isActive?: boolean; onOpen: () => void; onEdit: () => void; onDelete: () => void;
}) {
  const { data: sources, isLoading: loadingSources } = useQuery({
    queryKey: ["code-sources", projectId, asset.id],
    queryFn: () => codeSourcesApi.list(projectId, asset.id).then(r => r.data),
    enabled: !!projectId && !!asset.id,
  });
  const latest = Array.isArray(sources) ? sources[0] : undefined;
  const si = latest ? SOURCE_STATUS[latest.status] : null;

  return (
    <div className={cn("flex items-center justify-between px-3 py-2.5 bg-white border rounded-xl hover:shadow-sm transition-all group relative", isActive ? "border-blue-500 ring-1 ring-blue-500 shadow-sm" : "border-gray-200 hover:border-blue-300")}>
      <button onClick={onOpen} className="absolute inset-0 w-full h-full rounded-xl cursor-pointer" aria-label={`Abrir ${asset.name}`} />
      
      <div className="relative pointer-events-none flex items-center gap-3 flex-1 min-w-0 pr-2">
        <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-500 flex-shrink-0 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
          {TYPE_ICON[asset.asset_type] ?? <Server size={14} />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-gray-900 truncate leading-tight">{asset.name}</p>
          <div className="flex items-center gap-1.5 mt-0.5">
            {loadingSources ? (
              <span className="w-3 h-3 border border-gray-200 border-t-gray-400 rounded-full animate-spin flex-shrink-0" />
            ) : si ? (
              <>
                <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", si.dot)} />
                <span className="text-xs text-gray-400">{si.label}</span>
              </>
            ) : (
              <>
                <Circle size={7} className="text-gray-300 flex-shrink-0" />
                <span className="text-xs text-gray-400">Sin código</span>
              </>
            )}
          </div>
        </div>
        <span className={cn("text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0", CRIT_STYLES[asset.criticality])}>
          {CRIT_LABELS[asset.criticality]}
        </span>
      </div>

      <div className="relative z-10 flex items-center flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <Link
          href={`/activos/${asset.id}`}
          className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-md transition-colors"
          title="Configurar activo"
        >
          <Settings size={13} />
        </Link>
        <button
          onClick={e => { e.stopPropagation(); onEdit(); }}
          className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-md transition-colors"
          title="Editar activo"
        >
          <Edit2 size={13} />
        </button>
        <button
          onClick={e => { e.stopPropagation(); onDelete(); }}
          className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
          title="Eliminar activo"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}

// ─── Dashboard ───────────────────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { project, assetId, setAssetId } = useProjectStore();

  // Risk / matrix state
  const [page, setPage] = useState(1);

  // App creation state
  const [step, setStep] = useState<"list" | "new" | "edit">("list");
  const [app, setApp] = useState(BLANK_APP);
  const [editingAssetId, setEditingAssetId] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<ConfirmState>(null);

  // ── Queries ──────────────────────────────────────────────────
  const { data: assetsData, isLoading: assetsLoading } = useQuery({
    queryKey: ["assets", project?.id],
    queryFn: () => assetsApi.list(project!.id, { size: 50 }).then(r => r.data),
    enabled: !!project,
  });

  const { data: allRisks } = useQuery({
    queryKey: ["risks", "all", project?.id, assetId],
    queryFn: () => risksApi.list({ 
      project_id: project?.id, 
      asset_id: assetId !== "all" ? assetId : undefined, 
      size: 100 
    }).then(r => r.data),
    enabled: !!project,
  });

  const { data: pagedRisks } = useQuery({
    queryKey: ["risks", "paged", project?.id, assetId, page],
    queryFn: () => risksApi.list({ 
      project_id: project?.id, 
      asset_id: assetId !== "all" ? assetId : undefined, 
      size: PAGE_SIZE, 
      page 
    }).then(r => r.data),
    enabled: !!project,
  });

  const { data: summaryData } = useQuery({
    queryKey: ["risks", "matrix", project?.id, assetId],
    queryFn: () => risksApi.getMatrix(project?.id, assetId !== "all" ? assetId : undefined).then(r => r.data),
    enabled: !!project,
  });

  const { data: findingsData } = useQuery({
    queryKey: ["findings", "summary", project?.id, assetId],
    queryFn: () => findingsApi.list({
      project_id: project?.id,
      asset_id: assetId !== "all" ? assetId : undefined,
      size: 1
    }).then(r => r.data),
    enabled: !!project,
  });

  // ── Mutations ─────────────────────────────────────────────────
  const createAsset = useMutation({
    mutationFn: () => assetsApi.create(project!.id, {
      name: app.name, asset_type: app.asset_type, criticality: "medium",
      technical_owner: (app as any).technical_owner || null,
    }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      setStep("list");
      setApp(BLANK_APP);
      router.push(`/activos/${res.data.id}`);
    },
  });

  const updateAsset = useMutation({
    mutationFn: () => assetsApi.update(editingAssetId!, {
      name: app.name, asset_type: app.asset_type,
      technical_owner: (app as any).technical_owner || null,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      setStep("list");
      setApp(BLANK_APP);
      setEditingAssetId(null);
    },
  });

  const deleteAsset = useMutation({
    mutationFn: (id: string) => assetsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets"] }),
  });

  // ── Derived data ──────────────────────────────────────────────
  const assets: any[] = assetsData?.items ?? [];
  const risks: any[] = allRisks?.items ?? [];
  const summary = summaryData?.summary ?? {};
  const matrixGrid: number[][] = summaryData?.matrix ?? Array.from({ length: 5 }, () => Array(5).fill(0));
  const riskPositions: any[] = summaryData?.risks ?? [];
  const totalFindings = findingsData?.total ?? 0;
  const totalRisks = pagedRisks?.total ?? 0;
  const totalPages = pagedRisks?.pages ?? 1;

  return (
    <div className="space-y-5">
      {/* Confirm modal */}
      {confirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-gray-900 mb-2">{confirm.title}</h3>
            <p className="text-sm text-gray-500 mb-5">{confirm.desc}</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirm(null)}
                className="px-4 py-2 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg">
                Cancelar
              </button>
              <button onClick={() => { confirm.onConfirm(); setConfirm(null); }}
                className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg font-medium">
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-blue-600 mb-0.5">{project?.name}</p>
          <h1 className="text-2xl font-bold text-gray-900">Activos</h1>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 bg-white border border-gray-200 rounded-lg px-3 py-1.5">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          En vivo
        </div>
      </div>

      {/* ── Layout principal ─────────────────────────────────────── */}
      <div className="grid grid-cols-5 gap-5 items-start">

        {/* ── IZQUIERDA: Activos ──────────────────────────── */}
        <div className="col-span-2 space-y-3">

          {step === "new" || step === "edit" ? (
            /* ── Formulario nuevo/editar activo ── */
            <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 mb-1">
                <button onClick={() => { setStep("list"); setApp(BLANK_APP); setEditingAssetId(null); }}
                  className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                  <ArrowLeft size={14} />
                </button>
                <h2 className="text-sm font-semibold text-gray-800">{step === "new" ? "Nuevo activo" : "Editar activo"}</h2>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Nombre *</label>
                <input value={app.name} onChange={e => setApp(f => ({ ...f, name: e.target.value }))}
                  placeholder="Portal de pagos, API Auth…"
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tipo</label>
                <select value={app.asset_type} onChange={e => setApp(f => ({ ...f, asset_type: e.target.value }))}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                  {Object.entries(TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Responsable técnico</label>
                <input value={app.technical_owner} onChange={e => setApp(f => ({ ...f, technical_owner: e.target.value }))}
                  placeholder="equipo@empresa.com"
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
              </div>

              <div className="flex justify-end gap-2 pt-1">
                <button onClick={() => { setStep("list"); setApp(BLANK_APP); setEditingAssetId(null); }}
                  className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700">
                  Cancelar
                </button>
                <button onClick={() => step === "new" ? createAsset.mutate() : updateAsset.mutate()}
                  disabled={!app.name.trim() || createAsset.isPending || updateAsset.isPending}
                  className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl px-4 py-2">
                  {createAsset.isPending || updateAsset.isPending
                    ? <><Loader size={12} className="animate-spin" /> Guardando…</>
                    : <><Plus size={12} /> {step === "new" ? "Crear activo" : "Actualizar activo"}</>}
                </button>
              </div>
            </div>

          ) : (
            /* ── Lista de aplicaciones ── */
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-semibold text-gray-700">Activos</h2>
                  {assets.length > 0 && (
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{assets.length}</span>
                  )}
                </div>
                <button
                  onClick={() => setStep("new")}
                  className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-medium bg-blue-50 hover:bg-blue-100 px-2.5 py-1.5 rounded-lg transition-colors"
                >
                  <Plus size={11} /> Nueva
                </button>
              </div>

              {assetsLoading ? (
                <div className="space-y-2">
                  {[1, 2].map(i => (
                    <div key={i} className="h-14 bg-white border border-gray-200 rounded-xl animate-pulse" />
                  ))}
                </div>
              ) : assets.length === 0 ? (
                <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-8 text-center">
                  <AppWindow size={28} className="mx-auto mb-3 text-gray-200" />
                  <p className="text-sm text-gray-500 font-medium mb-1">Sin activos</p>
                  <p className="text-xs text-gray-400 mb-4">Registra el primer activo para comenzar.</p>
                  <button onClick={() => setStep("new")}
                    className="inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg px-3 py-2">
                    <Plus size={12} /> Nuevo activo
                  </button>
                </div>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                  {assets.map((asset: any) => (
                    <div key={asset.id} className="transition-all">
                      <AssetCardCompact
                        isActive={assetId === asset.id}
                        asset={asset}
                        projectId={project!.id}
                        onOpen={() => setAssetId(asset.id)}
                        onEdit={() => {
                          setApp({
                            name: asset.name,
                            asset_type: asset.asset_type,
                            technical_owner: asset.technical_owner || "",
                          } as any);
                          setEditingAssetId(asset.id);
                          setStep("edit");
                        }}
                        onDelete={() => setConfirm({
                          title: `¿Eliminar "${asset.name}"?`,
                          desc: "Se eliminarán también las fuentes de código, escaneos y hallazgos asociados.",
                          onConfirm: () => deleteAsset.mutate(asset.id),
                        })}
                      />
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* ── DERECHA: KPIs + Matriz + Riesgos ─────────────────── */}
        <div className="col-span-3 space-y-4">

          {/* KPIs */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: "Hallazgos", value: totalFindings, icon: <AlertTriangle size={14} />, color: "text-gray-600 bg-gray-50 border-gray-200" },
              { label: "Riesgos",   value: totalRisks,    icon: <Shield size={14} />,        color: "text-blue-600 bg-blue-50 border-blue-200" },
              { label: "Críticos",  value: summary.critical ?? 0, icon: <ShieldAlert size={14} />, color: "text-red-600 bg-red-50 border-red-200" },
              { label: "En trat.",  value: risks.filter(r => r.status === "in_progress").length, icon: <Activity size={14} />, color: "text-green-600 bg-green-50 border-green-200" },
            ].map(kpi => (
              <div key={kpi.label} className={cn("border rounded-xl p-3.5", kpi.color)}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium opacity-70">{kpi.label}</span>
                  {kpi.icon}
                </div>
                <p className="text-2xl font-bold">{kpi.value}</p>
              </div>
            ))}
          </div>

          {/* Lista de riesgos con paginación */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-800">Riesgos identificados</h3>
              <p className="text-xs text-gray-400">{totalRisks} en total</p>
            </div>

            {totalRisks === 0 ? (
              <div className="py-12 text-center text-gray-400 text-sm">
                Sin riesgos. Ejecuta el análisis desde Identificación.
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-100">
                        {["Código","Riesgo","Nivel","P×I","Estado"].map(h => (
                          <th key={h} className="text-left px-4 py-2.5 text-gray-400 font-medium uppercase tracking-wide">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(pagedRisks?.items ?? []).map((risk: any) => (
                        <tr key={risk.id} className="border-t border-gray-50 hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3 font-mono text-gray-400 whitespace-nowrap">{risk.risk_code ?? "—"}</td>
                          <td className="px-4 py-3 max-w-[180px]">
                            <p className="font-medium text-gray-800 truncate">{risk.risk_title}</p>
                          </td>
                          <td className="px-4 py-3">
                            <span className={cn("px-2 py-0.5 rounded border font-semibold whitespace-nowrap", LEVEL_COLOR[risk.risk_level])}>
                              {LEVEL_LABELS[risk.risk_level] ?? risk.risk_level}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-gray-600 whitespace-nowrap">
                            {risk.probability} × {risk.impact}
                            <span className="ml-1 text-gray-400">= {risk.risk_score}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={cn("px-2 py-0.5 rounded-full font-medium whitespace-nowrap", STATUS_COLOR[risk.status])}>
                              {STATUS_LABELS[risk.status] ?? risk.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {totalPages > 1 && (
                  <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
                    <span className="text-xs text-gray-400">
                      Página {page} de {totalPages} · {totalRisks} riesgos
                    </span>
                    <div className="flex items-center gap-1">
                      <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                        className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed">
                        <ChevronLeft size={13} />
                      </button>
                      {Array.from({ length: totalPages }, (_, i) => i + 1)
                        .filter(n => n === 1 || n === totalPages || Math.abs(n - page) <= 1)
                        .reduce((acc: (number | "...")[], n, idx, arr) => {
                          if (idx > 0 && n - (arr[idx - 1] as number) > 1) acc.push("...");
                          acc.push(n);
                          return acc;
                        }, [])
                        .map((n, i) => n === "..." ? (
                          <span key={`d-${i}`} className="px-1 text-gray-300 text-xs">…</span>
                        ) : (
                          <button key={n} onClick={() => setPage(n as number)}
                            className={cn("w-7 h-7 rounded-lg text-xs font-medium transition-colors",
                              page === n ? "bg-blue-600 text-white" : "border border-gray-200 text-gray-600 hover:bg-gray-50")}>
                            {n}
                          </button>
                        ))}
                      <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                        className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed">
                        <ChevronRight size={13} />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
