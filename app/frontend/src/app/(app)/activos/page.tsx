"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, codeSourcesApi } from "@/lib/api";
import { useProjectStore } from "@/lib/project";
import {
  Globe, Code, Layers, Server,
  AppWindow, Plus, Loader, Trash2, Circle, ArrowLeft, Edit2, Settings,
  Database,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Asset meta ───────────────────────────────────────────────────
const TYPE_ICON: Record<string, React.ReactNode> = {
  web_app: <Layers size={14} />,
  mobile_app: <Globe size={14} />,
  api: <Code size={14} />,
  network_equipment: <Server size={14} />,
  server: <Server size={14} />,
  database: <Database size={14} />,
  other: <Code size={14} />,
  web_app_scan: <Layers size={14} />, // Legacy
  webapp: <Layers size={14} />,       // Legacy
  appmobil: <Globe size={14} />,      // Legacy
};
const TYPE_LABELS: Record<string, string> = {
  web_app: "Aplicación web",
  mobile_app: "Aplicación móvil",
  api: "API / Web Service",
  network_equipment: "Equipos de red",
  server: "Servidor / Infraestructura",
  database: "Base de datos",
  other: "Otros",
  web_app_scan: "Aplicación web", // Legacy
  webapp: "Aplicación web",       // Legacy
  appmobil: "Aplicación móvil",   // Legacy
};

// Dropdown options to avoid showing legacy duplicates
const ASSET_TYPE_OPTIONS = [
  { value: "web_app", label: "Aplicación web" },
  { value: "mobile_app", label: "Aplicación móvil" },
  { value: "api", label: "API / Web Service" },
  { value: "network_equipment", label: "Equipos de red" },
  { value: "server", label: "Servidor / Infraestructura" },
  { value: "database", label: "Base de datos" },
  { value: "other", label: "Otros" },
];
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

const BLANK_APP = {
  name: "", description: "", asset_type: "webapp", url: "", ip_address: "",
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
                <span className="text-xs text-gray-400">{TYPE_LABELS[asset.asset_type] || "Activo"}</span>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="relative z-10 flex items-center flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
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

// ─── Activos ──────────────────────────────────────────────────────
export default function ActivosPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { project, assetId, setAssetId } = useProjectStore();

  const [step, setStep] = useState<"list" | "new" | "edit">("list");
  const [app, setApp] = useState({ ...BLANK_APP, business_owner: "" });
  const [editingAssetId, setEditingAssetId] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<ConfirmState>(null);

  // ── Queries ──────────────────────────────────────────────────
  const { data: assetsData, isLoading: assetsLoading } = useQuery({
    queryKey: ["assets", project?.id],
    queryFn: () => assetsApi.list(project!.id, { size: 100 }).then(r => r.data),
    enabled: !!project,
  });

  // ── Mutations ─────────────────────────────────────────────────
  const createAsset = useMutation({
    mutationFn: () => assetsApi.create(project!.id, {
      name: app.name, asset_type: app.asset_type, criticality: "medium",
      description: (app as any).description || null,
      url: (app as any).url || null,
      ip_address: (app as any).ip_address || null,
      business_owner: (app as any).business_owner || null,
    }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      setStep("list");
      setApp({ ...BLANK_APP, business_owner: "" });
    },
  });

  const updateAsset = useMutation({
    mutationFn: () => assetsApi.update(editingAssetId!, {
      name: app.name, asset_type: app.asset_type,
      description: (app as any).description || null,
      url: (app as any).url || null,
      ip_address: (app as any).ip_address || null,
      business_owner: (app as any).business_owner || null,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      setStep("list");
      setApp({ ...BLANK_APP, business_owner: "" });
      setEditingAssetId(null);
    },
  });

  const deleteAsset = useMutation({
    mutationFn: (id: string) => assetsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets"] }),
  });

  // ── Derived data ──────────────────────────────────────────────
  const assets: any[] = assetsData?.items ?? [];
  const sortedAssets = [...assets].sort((a, b) => a.name.localeCompare(b.name));

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
      <div>

        {/* ── Activos ──────────────────────────── */}
        <div className="space-y-3">

          {step === "new" || step === "edit" ? (
            /* ── Formulario nuevo/editar activo ── */
            <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 mb-1">
                <button onClick={() => { setStep("list"); setApp({ ...BLANK_APP, business_owner: "" }); setEditingAssetId(null); }}
                  className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                  <ArrowLeft size={14} />
                </button>
                <h2 className="text-sm font-semibold text-gray-800">{step === "new" ? "Nuevo activo" : "Editar activo"}</h2>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Nombre *</label>
                <input value={app.name} onChange={e => setApp(f => ({ ...f, name: e.target.value }))}
                  placeholder="ACT-001 AppWeb..."
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Descripción</label>
                <textarea value={(app as any).description || ""} onChange={e => setApp(f => ({ ...f, description: e.target.value }))}
                  placeholder="Descripción del activo..."
                  rows={2}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none" />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Responsable</label>
                <input value={(app as any).business_owner || ""} onChange={e => setApp(f => ({ ...f, business_owner: e.target.value }))}
                  placeholder="Dpto. Sistemas, Juan Pérez..."
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tipo</label>
                <select value={app.asset_type} onChange={e => setApp(f => ({ ...f, asset_type: e.target.value }))}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                  {ASSET_TYPE_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">URL</label>
                <input value={(app as any).url || ""} onChange={e => setApp(f => ({ ...f, url: e.target.value }))}
                  placeholder="https://..."
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Dirección IP</label>
                <input value={(app as any).ip_address || ""} onChange={e => setApp(f => ({ ...f, ip_address: e.target.value }))}
                  placeholder="192.168.1.1"
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
              </div>

              <div className="flex justify-between items-center pt-2 mt-4 border-t border-gray-100">
                {step === "edit" && editingAssetId ? (
                  <Link
                    href={`/activos/${editingAssetId}`}
                    className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-2 rounded-lg transition-colors"
                  >
                    <Settings size={13} />
                    Agregar código fuente
                  </Link>
                ) : (
                  <div />
                )}
                <div className="flex gap-2">
                  <button onClick={() => { setStep("list"); setApp({ ...BLANK_APP, business_owner: "" }); setEditingAssetId(null); }}
                    className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700">
                    Cancelar
                  </button>
                  <button onClick={() => step === "new" ? createAsset.mutate() : updateAsset.mutate()}
                    disabled={!app.name.trim() || createAsset.isPending || updateAsset.isPending}
                    className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl px-4 py-2">
                    {createAsset.isPending || updateAsset.isPending
                      ? <><Loader size={12} className="animate-spin" /> Guardando…</>
                      : <><Plus size={12} /> {step === "new" ? "Crear" : "Actualizar"}</>}
                  </button>
                </div>
              </div>
            </div>

          ) : (
            /* ── Lista de aplicaciones ── */
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-semibold text-gray-700">Activos</h2>
                  {sortedAssets.length > 0 && (
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{sortedAssets.length}</span>
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
              ) : sortedAssets.length === 0 ? (
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
                <div className="grid grid-cols-3 gap-3">
                  {sortedAssets.map((asset: any) => (
                    <div key={asset.id} className="transition-all">
                      <AssetCardCompact
                        isActive={assetId === asset.id}
                        asset={asset}
                        projectId={project!.id}
                        onOpen={() => setAssetId(asset.id)}
                        onEdit={() => {
                          setApp({
                            name: asset.name,
                            description: asset.description || "",
                            asset_type: asset.asset_type,
                            url: asset.url || "",
                            ip_address: asset.ip_address || "",
                            business_owner: asset.business_owner || "",
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
      </div>

    </div>
  );
}
