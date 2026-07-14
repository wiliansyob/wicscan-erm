"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, codeSourcesApi, scanSessionsApi } from "@/lib/api";
import { useProjectStore } from "@/lib/project";
import {
  ArrowLeft, Github, Upload, Play, Loader, CheckCircle,
  XCircle, Clock, AlertTriangle, RefreshCw, Plus, ExternalLink,
  Trash2, StopCircle, Save
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

type Tab = "Código fuente" | "Contexto IA";


const STATUS_ICON: Record<string, React.ReactNode> = {
  pending:   <Clock size={13} className="text-gray-400" />,
  running:   <Loader size={13} className="text-blue-500 animate-spin" />,
  completed: <CheckCircle size={13} className="text-green-500" />,
  failed:    <XCircle size={13} className="text-red-500" />,
  cancelled: <XCircle size={13} className="text-gray-400" />,
  ready:     <CheckCircle size={13} className="text-green-500" />,
  error:     <XCircle size={13} className="text-red-500" />,
  cloning:   <Loader size={13} className="text-blue-500 animate-spin" />,
};

type ConfirmState = { title: string; desc: string; action?: string; onConfirm: () => void } | null;

export default function AppDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { project } = useProjectStore();
  const [tab, setTab] = useState<Tab>("Código fuente");
  const [readmeText, setReadmeText] = useState<string | null>(null);
  const [showAddSource, setShowAddSource] = useState(false);
  const [srcForm, setSrcForm] = useState({ source_type: "github" as "github" | "zip", github_url: "", github_branch: "", github_token: "", zipFile: null as File | null });
  const [confirm, setConfirm] = useState<ConfirmState>(null);

  const { data: asset } = useQuery({
    queryKey: ["asset", id],
    queryFn: () => assetsApi.get(id).then(r => r.data),
    enabled: !!id,
  });

  const { data: sources, isLoading: loadingSources } = useQuery({
    queryKey: ["code-sources", project?.id, id],
    queryFn: () => codeSourcesApi.list(project!.id, id).then(r => r.data),
    enabled: !!project && !!id,
    refetchInterval: (query: any) => query.state.data?.some((s: any) => s.status === "cloning") ? 4000 : false,
  });


  const addSourceMutation = useMutation({
    mutationFn: () => {
      if (srcForm.source_type === "zip" && srcForm.zipFile) {
        return codeSourcesApi.uploadZip(project!.id, srcForm.zipFile, {
          label: srcForm.zipFile.name,
          asset_id: id,
        });
      }
      return codeSourcesApi.create(project!.id, {
        source_type: srcForm.source_type,
        label: srcForm.source_type === "github" ? (srcForm.github_url.split("/").pop() || asset?.name) : asset?.name,
        asset_id: id,
        github_url: srcForm.source_type === "github" ? srcForm.github_url : undefined,
        github_branch: srcForm.github_branch,
        github_token: srcForm.github_token || undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["code-sources"] });
      setShowAddSource(false);
      setSrcForm({ source_type: "github", github_url: "", github_branch: "", github_token: "", zipFile: null });
    },
  });

  const deleteSourceMutation = useMutation({
    mutationFn: (csId: string) => codeSourcesApi.delete(csId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["code-sources"] }),
  });


  const deleteAssetMutation = useMutation({
    mutationFn: () => assetsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      router.push("/activos");
    },
  });

  const saveReadmeMutation = useMutation({
    mutationFn: (content: string) => assetsApi.update(id, { readme_content: content || null }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["asset", id] }),
  });

  const readySources = (sources ?? []).filter((s: any) => s.status === "ready");

  const askConfirm = (c: NonNullable<ConfirmState>) => setConfirm(c);

  const availableTabs = ["Código fuente", "Contexto IA"];
  const activeTab = tab;

  return (
    <div className="space-y-6">
      {/* Confirmation modal */}
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

      {/* Header */}
      <div>
        <button onClick={() => router.back()} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-700 mb-3 transition-colors">
          <ArrowLeft size={13} /> Volver
        </button>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-blue-600 mb-1">{project?.name}</p>
            <h1 className="text-2xl font-bold text-gray-900">{asset?.name ?? "Cargando…"}</h1>
            {asset?.description && <p className="text-sm text-gray-500 mt-0.5">{asset.description}</p>}
          </div>
          <div className="flex items-center gap-3">
            {asset && (
              <div className="flex items-center gap-3 text-xs text-gray-500">
                {asset.ip_address && <span>IP: {asset.ip_address}</span>}
                {asset.url && (
                  <a href={asset.url} target="_blank" rel="noreferrer"
                    className="flex items-center gap-1 text-blue-500 hover:text-blue-700">
                    <ExternalLink size={11} /> {asset.url}
                  </a>
                )}
              </div>
            )}
            <button
              onClick={() => askConfirm({
                title: `¿Eliminar "${asset?.name}"?`,
                desc: "Se eliminarán también todas las fuentes de código, sesiones de escaneo y hallazgos asociados. Esta acción no se puede deshacer.",
                onConfirm: () => deleteAssetMutation.mutate(),
              })}
              className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded-lg border border-red-200 transition-colors">
              <Trash2 size={12} /> Eliminar activo
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-6">
          {availableTabs.map(t => (
            <button key={t} onClick={() => setTab(t as Tab)}
              className={cn("pb-3 text-sm font-medium border-b-2 transition-colors",
                activeTab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-800")}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* TAB: Código fuente */}
      {activeTab === "Código fuente" && (
        <div className="space-y-4">
          {loadingSources ? (
            <div className="text-gray-400 text-sm py-8 text-center">Cargando fuentes…</div>
          ) : (
            <>
              {(sources ?? []).map((src: any) => (
                <div key={src.id} className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {src.source_type === "github"
                      ? <Github size={20} className="text-gray-600 flex-shrink-0" />
                      : <Upload size={20} className="text-gray-600 flex-shrink-0" />}
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{src.label ?? src.github_url}</p>
                      {src.github_url && <p className="text-xs text-gray-400 font-mono">{src.github_url} @ {src.github_branch}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <div className="flex items-center gap-2">
                      {STATUS_ICON[src.status]}
                      <span className={cn("font-medium",
                        src.status === "ready" ? "text-green-600" :
                        src.status === "error" ? "text-red-500" :
                        src.status === "cloning" ? "text-blue-600" : "text-gray-500")}>
                        {{ ready: "Listo para escanear", cloning: "Clonando…", pending: "Pendiente", error: "Error al clonar" }[src.status as string] ?? src.status}
                      </span>
                      {src.ready_at && <span className="text-gray-300">· {format(new Date(src.ready_at), "d MMM HH:mm")}</span>}
                    </div>
                    <button
                      onClick={() => askConfirm({
                        title: "¿Eliminar fuente de código?",
                        desc: "Se eliminarán también las sesiones de escaneo y hallazgos vinculados.",
                        onConfirm: () => deleteSourceMutation.mutate(src.id),
                      })}
                      className="text-gray-300 hover:text-red-400 transition-colors ml-2">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}

              {showAddSource ? (
                <div className="bg-white border border-blue-200 rounded-xl p-5 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    {(["github", "zip"] as const).map(t => (
                      <button key={t} onClick={() => setSrcForm(f => ({ ...f, source_type: t }))}
                        className={cn("flex items-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium",
                          srcForm.source_type === t ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600 hover:border-gray-300")}>
                        {t === "github" ? <Github size={15} /> : <Upload size={15} />}
                        {t === "github" ? "GitHub" : "ZIP"}
                      </button>
                    ))}
                  </div>
                  {srcForm.source_type === "github" && (
                    <div className="space-y-3">
                      <input value={srcForm.github_url} onChange={e => setSrcForm(f => ({ ...f, github_url: e.target.value }))}
                        placeholder="https://github.com/org/repo"
                        className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500" />
                      <input value={srcForm.github_branch} onChange={e => setSrcForm(f => ({ ...f, github_branch: e.target.value }))}
                        placeholder="Rama a escanear (Opcional) - Si se deja vacío, usa la predeterminada"
                        className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500" />
                      <input type="password" autoComplete="current-password" value={srcForm.github_token} onChange={e => setSrcForm(f => ({ ...f, github_token: e.target.value }))}
                        placeholder="Token de Acceso (Opcional) - Requerido para repositorios privados"
                        className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {srcForm.source_type === "zip" && (
                    <label className={cn(
                      "flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-6 cursor-pointer transition-all",
                      srcForm.zipFile ? "border-blue-400 bg-blue-50" : "border-gray-200 hover:border-blue-300"
                    )}>
                      <input type="file" accept=".zip" className="hidden"
                        onChange={e => setSrcForm(f => ({ ...f, zipFile: e.target.files?.[0] ?? null }))} />
                      <Upload size={20} className={cn("mb-1.5", srcForm.zipFile ? "text-blue-500" : "text-gray-300")} />
                      {srcForm.zipFile ? (
                        <p className="text-sm font-medium text-blue-700">{srcForm.zipFile.name}</p>
                      ) : (
                        <p className="text-sm text-gray-400">Clic para seleccionar .zip</p>
                      )}
                    </label>
                  )}
                  <div className="flex justify-end gap-3">
                    <button onClick={() => setShowAddSource(false)} className="text-sm text-gray-500 hover:text-gray-700 px-3 py-2">Cancelar</button>
                    <button onClick={() => addSourceMutation.mutate()}
                      disabled={(srcForm.source_type === "github" && !srcForm.github_url.trim()) || (srcForm.source_type === "zip" && !srcForm.zipFile) || addSourceMutation.isPending}
                      className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl px-4 py-2">
                      {addSourceMutation.isPending ? <><Loader size={12} className="animate-spin" /> Registrando…</> : "Agregar"}
                    </button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setShowAddSource(true)}
                  className="w-full flex items-center justify-center gap-2 border-2 border-dashed border-gray-200 hover:border-blue-300 rounded-xl p-4 text-sm text-gray-400 hover:text-blue-600 transition-all">
                  <Plus size={14} /> Agregar fuente de código
                </button>
              )}
            </>
          )}
        </div>
      )}


      {/* TAB: Contexto IA */}
      {activeTab === "Contexto IA" && (
        <div className="space-y-4 max-w-3xl">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-gray-600">README / Documentación del proyecto</label>
              <label className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 cursor-pointer">
                <Upload size={11} /> Cargar archivo
                <input type="file" accept=".md,.txt,.rst" className="hidden"
                  onChange={e => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    const reader = new FileReader();
                    reader.onload = ev => setReadmeText(ev.target?.result as string ?? "");
                    reader.readAsText(file);
                    e.target.value = "";
                  }} />
              </label>
            </div>
            <textarea
              value={readmeText ?? (asset?.readme_content ?? "")}
              onChange={e => setReadmeText(e.target.value)}
              rows={18}
              placeholder={"# Mi Aplicación\n\n## ¿Qué hace?\nDescribe aquí el propósito de la aplicación...\n\n## Datos que maneja\n- Datos personales de usuarios\n- Información financiera\n\n## Stack tecnológico\n- Next.js 14, Node.js\n- PostgreSQL, Redis"}
              className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-xs font-mono leading-relaxed focus:outline-none focus:border-blue-400 resize-none"
            />
            {(readmeText ?? asset?.readme_content) && (
              <p className="text-xs text-gray-400 mt-1">
                {(readmeText ?? asset?.readme_content ?? "").split("\n").length} líneas
              </p>
            )}
          </div>
          <div className="flex justify-end gap-3">
            {readmeText !== null && readmeText !== (asset?.readme_content ?? "") && (
              <button onClick={() => setReadmeText(null)} className="text-sm text-gray-500 hover:text-gray-700 px-3 py-2">
                Descartar cambios
              </button>
            )}
            <button
              onClick={() => saveReadmeMutation.mutate(readmeText ?? asset?.readme_content ?? "")}
              disabled={saveReadmeMutation.isPending || (readmeText === null)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-sm font-medium rounded-xl px-5 py-2.5">
              {saveReadmeMutation.isPending
                ? <><Loader size={13} className="animate-spin" /> Guardando…</>
                : <><Save size={13} /> Guardar README</>}
            </button>
          </div>
          {saveReadmeMutation.isSuccess && (
            <p className="text-xs text-green-600 flex items-center gap-1.5">
              <CheckCircle size={12} /> README guardado — se usará en el próximo análisis de riesgos
            </p>
          )}
        </div>
      )}


    </div>
  );
}
