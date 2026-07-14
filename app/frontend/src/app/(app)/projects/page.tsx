"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "@/lib/api";
import { useProjectStore } from "@/lib/project";
import {
  ShieldAlert, Plus, FolderOpen, ArrowRight,
  X, Loader, Trash2, Edit2
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Apetito de riesgo ───────────────────────────────────────────
const APPETITE_OPTIONS = [
  { value: "low",      label: "Bajo",     desc: "Poca tolerancia al riesgo — sectores regulados" },
  { value: "medium",   label: "Medio",    desc: "Equilibrio entre seguridad y velocidad" },
  { value: "high",     label: "Alto",     desc: "Alta tolerancia — entornos de experimentación" },
  { value: "critical", label: "Crítico",  desc: "Infraestructura crítica — tolerancia cero" },
];

const APPETITE_STYLES: Record<string, string> = {
  low:      "bg-blue-50 border-blue-200 text-blue-800",
  medium:   "bg-yellow-50 border-yellow-200 text-yellow-800",
  high:     "bg-orange-50 border-orange-200 text-orange-800",
  critical: "bg-red-50 border-red-200 text-red-800",
};

type ConfirmState = { title: string; desc: string; onConfirm: () => void } | null;

export default function ProjectsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { project: activeProject, setProject, clearProject } = useProjectStore();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    risk_appetite: "medium",
    business_context: "",
  });

  const handleOpenCreate = () => {
    setForm({ name: "", description: "", risk_appetite: "medium", business_context: "" });
    setEditingId(null);
    setShowForm(true);
  };

  const handleOpenEdit = (p: any, e: React.MouseEvent) => {
    e.stopPropagation();
    setForm({
      name: p.name,
      description: p.description || "",
      risk_appetite: p.risk_appetite || "medium",
      business_context: p.business_context || "",
    });
    setEditingId(p.id);
    setShowForm(true);
  };

  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list({ size: 50 }).then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      projectsApi.create({
        name: form.name,
        description: form.description || null,
        risk_appetite: form.risk_appetite,
        business_context: form.business_context || null,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      openProject(res.data);
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      projectsApi.update(editingId!, {
        name: form.name,
        description: form.description || null,
        risk_appetite: form.risk_appetite,
        business_context: form.business_context || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => projectsApi.delete(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      if (activeProject?.id === id) clearProject();
    },
  });

  const openProject = (p: any) => {
    setProject(p);
    router.push("/dashboard");
  };

  const projects = data?.items ?? [];

  return (
    <div className="min-h-screen">
      {/* Confirmation modal */}
      {confirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-gray-900 mb-2">{confirm.title}</h3>
            <p className="text-sm text-gray-500 mb-5">{confirm.desc}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirm(null)}
                className="px-4 py-2 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => { confirm.onConfirm(); setConfirm(null); }}
                className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors"
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Evaluaciones de Riesgo</h1>
          <p className="text-sm text-gray-500 mt-1">
            Cada proyecto es una evaluación independiente y aislada. Los riesgos no se mezclan entre proyectos.
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl px-4 py-2.5 transition-all shadow-sm shadow-blue-200"
        >
          <Plus size={16} />
          Nueva evaluación
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="mb-8 bg-white border border-blue-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-gray-900">
              {editingId ? "Editar evaluación de riesgo" : "Nueva evaluación de riesgo"}
            </h2>
            <button onClick={() => { setShowForm(false); setEditingId(null); }} className="text-gray-400 hover:text-gray-600">
              <X size={18} />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Nombre del proyecto *</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="ej. API de Pagos, Portal Web, Microservicio Auth…"
                className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 transition-all placeholder-gray-400"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Descripción</label>
              <input
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Breve descripción del sistema o componente a evaluar"
                className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 transition-all placeholder-gray-400"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Apetito de riesgo</label>
              <div className="grid grid-cols-2 gap-2">
                {APPETITE_OPTIONS.map(({ value, label, desc }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, risk_appetite: value }))}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      form.risk_appetite === value
                        ? APPETITE_STYLES[value]
                        : "bg-white border-gray-200 text-gray-600 hover:border-gray-300"
                    }`}
                  >
                    <p className="text-xs font-semibold">{label}</p>
                    <p className="text-xs opacity-70 mt-0.5 leading-tight">{desc}</p>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Contexto de negocio</label>
              <textarea
                value={form.business_context}
                onChange={(e) => setForm((f) => ({ ...f, business_context: e.target.value }))}
                placeholder="Describe el impacto potencial al negocio, regulaciones aplicables, datos que maneja…"
                rows={5}
                className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 transition-all placeholder-gray-400 resize-none"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-5">
            <button
              onClick={() => { setShowForm(false); setEditingId(null); }}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={() => editingId ? updateMutation.mutate() : createMutation.mutate()}
              disabled={!form.name.trim() || createMutation.isPending || updateMutation.isPending}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl px-5 py-2.5 transition-all"
            >
              {createMutation.isPending || updateMutation.isPending ? (
                <><Loader size={14} className="animate-spin" /> Guardando…</>
              ) : editingId ? (
                "Guardar cambios"
              ) : (
                <><Plus size={14} /> Crear y abrir</>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Project list */}
      {isLoading ? (
        <div className="grid grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-2xl p-5 animate-pulse">
              <div className="h-4 bg-gray-100 rounded w-3/4 mb-3" />
              <div className="h-3 bg-gray-100 rounded w-1/2 mb-6" />
              <div className="h-8 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center mb-4">
            <ShieldAlert size={28} className="text-blue-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Crea tu primera evaluación</h2>
          <p className="text-gray-500 text-sm max-w-sm mb-6">
            Cada evaluación analiza un proyecto de forma independiente. Los riesgos, hallazgos y análisis son completamente aislados.
          </p>
          <button
            onClick={handleOpenCreate}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl px-5 py-3 transition-all"
          >
            <Plus size={16} /> Nueva evaluación
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-5">
          {projects.map((p: any) => (
            <div
              key={p.id}
              className="bg-white border border-gray-200 rounded-2xl p-5 hover:border-blue-300 hover:shadow-md transition-all group cursor-pointer flex flex-col relative"
              onClick={() => openProject(p)}
            >
              {/* Actions */}
              <div className="absolute top-3 right-3 z-10 flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
                <button
                  onClick={(e) => handleOpenEdit(p, e)}
                  className="p-1.5 text-gray-300 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <Edit2 size={13} />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirm({
                      title: `¿Eliminar "${p.name}"?`,
                      desc: "Se eliminarán todas las aplicaciones, escaneos, hallazgos y riesgos del proyecto. Esta acción no se puede deshacer.",
                      onConfirm: () => deleteMutation.mutate(p.id),
                    });
                  }}
                  className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 size={13} />
                </button>
              </div>

              {/* Ícono + apetito */}
              <div className="flex items-start justify-between mb-3">
                <div className="w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                  <FolderOpen size={16} className="text-blue-500" />
                </div>
                <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium mr-7", APPETITE_STYLES[p.risk_appetite])}>
                  {APPETITE_OPTIONS.find((o) => o.value === p.risk_appetite)?.label ?? p.risk_appetite}
                </span>
              </div>

              {/* Nombre y descripción */}
              <h3 className="text-sm font-bold text-gray-900 mb-1 group-hover:text-blue-700 transition-colors">
                {p.name}
              </h3>
              {p.description && (
                <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{p.description}</p>
              )}

              <div className="mt-auto pt-4">
                {/* Conteo de activos */}
                <div className="flex items-center gap-1.5 py-3 border-t border-gray-100">
                  <div className="w-2 h-2 rounded-full bg-blue-400" />
                  <span className="text-xs text-gray-500">
                    {p.asset_count} activo{p.asset_count !== 1 ? "s" : ""}
                  </span>
                </div>

                <button
                  onClick={(e) => { e.stopPropagation(); openProject(p); }}
                  className="w-full flex items-center justify-center gap-2 text-sm text-blue-600 font-medium py-2 rounded-xl bg-blue-50 hover:bg-blue-100 transition-all mt-1"
                >
                  Abrir evaluación <ArrowRight size={14} />
                </button>
              </div>
            </div>
          ))}

          {/* Nueva evaluación */}
          <button
            onClick={handleOpenCreate}
            className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-2xl p-5 hover:border-blue-300 hover:bg-blue-50/30 transition-all flex flex-col items-center justify-center gap-3 text-gray-400 hover:text-blue-500 min-h-[200px]"
          >
            <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
              <Plus size={18} />
            </div>
            <span className="text-sm font-medium">Nueva evaluación</span>
          </button>
        </div>
      )}
    </div>
  );
}
