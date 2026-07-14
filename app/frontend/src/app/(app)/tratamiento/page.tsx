"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { risksApi, workspacesApi } from "@/lib/api";
import { useProjectStore } from "@/lib/project";
import { ShieldCheck, Plus, Loader, ChevronDown, ChevronUp, User, Calendar, X, Sparkles, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

const TREATMENT_TYPES = [
  { value: "mitigate", label: "Reducir", desc: "Implementar controles para reducir el riesgo", color: "bg-blue-100 text-blue-700 border-blue-200" },
  { value: "avoid",    label: "Evitar",  desc: "Eliminar la actividad que genera el riesgo",  color: "bg-red-100 text-red-700 border-red-200" },
  { value: "transfer", label: "Transferir", desc: "Seguro, externalización o contrato",       color: "bg-purple-100 text-purple-700 border-purple-200" },
  { value: "accept",   label: "Aceptar", desc: "Riesgo dentro del apetito de riesgo",         color: "bg-green-100 text-green-700 border-green-200" },
];

const PRIORITY_LABELS: Record<string, string> = {
  immediate: "Inmediato", short_term: "Corto plazo", medium_term: "Mediano plazo", long_term: "Largo plazo",
};

const LEVEL_BG: Record<string, string> = {
  critical: "bg-red-600", high: "bg-orange-500", medium: "bg-yellow-400", low: "bg-green-400",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Abierto", in_progress: "En proceso", mitigated: "Mitigado", accepted: "Aceptado",
};

const BLANK_TREATMENT = {
  treatment_type: "mitigate",
  title: "",
  description: "",
  owner_name: "",
  due_date: "",
  priority: "medium_term",
  acceptance_justification: "",
  expected_risk_reduction: "",
};

const PRIORITY_ORDER: Record<string, number> = {
  immediate: 4, short_term: 3, medium_term: 2, long_term: 1
};

const DEFAULT_AI_PROVIDERS = [
  { value: "anthropic", label: "Anthropic Claude", models: ["claude-3-5-sonnet-20241022"] },
  { value: "gemini",    label: "Google Gemini",    models: ["gemini-flash-latest"] },
  { value: "ollama",    label: "Ollama (local)",   models: ["llama3.2"] },
];

export default function TratamientoPage() {
  const qc = useQueryClient();
  const { project } = useProjectStore();
  const [expandedRisk, setExpandedRisk] = useState<string | null>(null);
  const [addingTo, setAddingTo] = useState<string | null>(null);
  const [editingTreatment, setEditingTreatment] = useState<string | null>(null);
  const [form, setForm] = useState(BLANK_TREATMENT);
  const [aiProvider, setAiProvider] = useState("gemini");
  const [aiModel, setAiModel]       = useState("");
  const [suggestingFor, setSuggestingFor] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const { data: settingsData } = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: () => workspacesApi.getSettings().then(res => res.data),
  });

  const availableProviders: { value: string; label: string; model: string }[] = (() => {
    const config = settingsData?.ai_config;
    if (!config?.providers) return [];
    const list: { value: string; label: string; model: string }[] = [];
    Object.keys(config.providers).forEach(key => {
      const prov = config.providers[key];
      if (!prov || !prov.enabled) return;
      const model = prov.model || "";
      if (key.startsWith("custom_")) {
        if (prov.api_key && prov.url) list.push({ value: key, label: prov.label || prov.name || key, model });
      } else if (key === "ollama") {
        list.push({ value: key, label: "Ollama (local)", model });
      } else if (prov.api_key) {
        const match = DEFAULT_AI_PROVIDERS.find(p => p.value === key);
        if (match) list.push({ value: key, label: match.label, model });
      }
    });
    return list;
  })();

  useEffect(() => {
    if (availableProviders.length === 0) return;
    const current = availableProviders.find(p => p.value === aiProvider) ?? availableProviders[0];
    if (!availableProviders.find(p => p.value === aiProvider)) setAiProvider(current.value);
    setAiModel(current.model);
  }, [settingsData]);

  const { data: risksData, isLoading } = useQuery({
    queryKey: ["risks-treatment", project?.id],
    queryFn: () => risksApi.list({ project_id: project?.id, size: 100 }).then(r => r.data),
    enabled: !!project,
  });

  const risks: any[] = (risksData?.items ?? [])
    .filter((r: any) => r.status !== "mitigated" && r.status !== "accepted")
    .sort((a: any, b: any) => {
      const prioA = PRIORITY_ORDER[a.priority ?? ""] ?? 0;
      const prioB = PRIORITY_ORDER[b.priority ?? ""] ?? 0;
      if (prioB !== prioA) return prioB - prioA;
      const scoreA = a.risk_score || (a.probability * a.impact) || 0;
      const scoreB = b.risk_score || (b.probability * b.impact) || 0;
      return scoreB - scoreA;
    });

  const addTreatmentMutation = useMutation({
    mutationFn: (riskId: string) => risksApi.addTreatment(riskId, {
      treatment_type: form.treatment_type,
      title: form.title,
      description: form.description || null,
      owner_name: form.owner_name || null,
      due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
      priority: form.priority,
      acceptance_justification: form.treatment_type === "accept" ? form.acceptance_justification : null,
      expected_risk_reduction: form.expected_risk_reduction ? Number(form.expected_risk_reduction) : null,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risks-treatment"] });
      qc.invalidateQueries({ queryKey: ["risks"] });
      setAddingTo(null);
      setForm(BLANK_TREATMENT);
      setForm(BLANK_TREATMENT);
    },
  });

  const updateTreatmentMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => risksApi.updateTreatment(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risks-treatment"] });
      qc.invalidateQueries({ queryKey: ["risks"] });
      setEditingTreatment(null);
      setForm(BLANK_TREATMENT);
    },
  });

  const deleteTreatmentMutation = useMutation({
    mutationFn: (treatmentId: string) => risksApi.deleteTreatment(treatmentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risks-treatment"] });
      qc.invalidateQueries({ queryKey: ["risks"] });
    },
  });

  const suggestMutation = useMutation({
    mutationFn: (riskId: string) => risksApi.suggestTreatments(riskId, aiProvider, aiModel || undefined),
    onSuccess: (res, riskId) => {
      const actions: any[] = res.data?.actions ?? [];
      setSuggestions(actions);
      setSuggestingFor(riskId);
      setAddingTo(null);
    },
  });

  const handleExport = async () => {
    if (!project) return;
    setExporting(true);
    setExportError(null);
    try {
      await risksApi.exportTreatmentsExcel(project.id, project.name);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Error al exportar");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-blue-600 mb-1">{project?.name}</p>
          <h1 className="text-2xl font-bold text-gray-900">Plan de Tratamiento</h1>
          <p className="text-sm text-gray-500 mt-0.5">Define acciones para reducir, evitar, transferir o aceptar cada riesgo.</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-3">
            <button
              onClick={handleExport}
              disabled={exporting}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              {exporting ? <Loader size={15} className="animate-spin" /> : <Sparkles size={15} />}
              {exporting ? "Exportando..." : "Exportar Excel"}
            </button>
          </div>
          {exportError && (
            <p className="text-xs text-red-600">{exportError}</p>
          )}
        </div>
      </div>

      {/* Treatment type legend */}
      <div className="flex flex-wrap gap-2">
        {TREATMENT_TYPES.map(t => (
          <span key={t.value} className={cn("text-xs px-3 py-1 rounded-full border font-medium", t.color)}>
            {t.label}
          </span>
        ))}
      </div>

      {isLoading ? (
        <div className="text-gray-400 text-sm py-8 text-center">Cargando riesgos…</div>
      ) : risks.length === 0 ? (
        <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-12 text-center">
          <ShieldCheck size={32} className="mx-auto mb-3 text-gray-200" />
          <p className="text-gray-400 text-sm">Sin riesgos pendientes de tratamiento.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {risks.map(risk => {
            const expanded = expandedRisk === risk.id;
            const addingHere = addingTo === risk.id;
            const treatments: any[] = (risk.treatments ?? []).sort((a: any, b: any) => {
              return (PRIORITY_ORDER[b.priority ?? ""] ?? 0) - (PRIORITY_ORDER[a.priority ?? ""] ?? 0);
            });
            return (
              <div key={risk.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                {/* Risk header */}
                <button
                  onClick={() => setExpandedRisk(expanded ? null : risk.id)}
                  className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-gray-50 transition-colors">
                  <span className={cn("text-xs font-bold px-2 py-1 rounded text-white flex-shrink-0", LEVEL_BG[risk.risk_level])}>
                    {risk.risk_code ?? "R-?"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 truncate">{risk.risk_title}</p>
                    <p className="text-xs text-gray-400 mt-0.5">Score: {risk.risk_score} · {STATUS_LABELS[risk.status] ?? risk.status}</p>
                  </div>
                  
                  {/* Vista previa de acciones */}
                  <div className="hidden lg:flex flex-col items-end justify-center mr-2 w-1/3 flex-shrink-0">
                    {treatments.length > 0 ? (
                      <div className="w-full space-y-1">
                        {treatments.slice(0, 2).map((t: any) => {
                          const ttype = TREATMENT_TYPES.find(x => x.value === t.treatment_type);
                          return (
                            <div key={t.id} className="flex items-center justify-end gap-1.5 text-[11px] text-gray-600 truncate w-full">
                              <span className={cn("px-1.5 py-0.5 rounded border leading-none font-semibold text-[9px] flex-shrink-0", ttype?.color)}>
                                {ttype?.label}
                              </span>
                              <span className="truncate">{t.title}</span>
                              {t.due_date && <span className="text-gray-400 flex-shrink-0">({format(new Date(t.due_date), "d MMM")})</span>}
                            </div>
                          );
                        })}
                        {treatments.length > 2 && (
                          <div className="text-[10px] text-gray-400 text-right pr-1">+{treatments.length - 2} acciones más...</div>
                        )}
                      </div>
                    ) : (
                      <span className="text-[11px] text-gray-400 italic">No hay acciones definidas</span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    {treatments.length > 0 && (
                      <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-2.5 py-0.5">
                        {treatments.length} acción{treatments.length !== 1 ? "es" : ""}
                      </span>
                    )}
                    {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
                  </div>
                </button>

                {expanded && (
                  <div className="border-t border-gray-100 px-5 py-4 space-y-4">
                    {/* Existing treatments */}
                    {treatments.length > 0 && (
                      <div className="space-y-2">
                        {treatments.map((t: any) => {
                          if (editingTreatment === t.id) {
                            return (
                              <div key={t.id} className="border border-blue-200 rounded-xl p-4 bg-blue-50/30 space-y-4">
                                <div className="flex items-center justify-between">
                                  <p className="text-sm font-semibold text-gray-800">Editar acción de tratamiento</p>
                                  <button onClick={() => { setEditingTreatment(null); setForm(BLANK_TREATMENT); }}>
                                    <X size={15} className="text-gray-400 hover:text-gray-700" />
                                  </button>
                                </div>
                                <div className="grid grid-cols-4 gap-2">
                                  {TREATMENT_TYPES.map(type => (
                                    <button key={type.value} onClick={() => setForm(f => ({ ...f, treatment_type: type.value }))}
                                      className={cn("p-3 rounded-lg border-2 text-center transition-all",
                                        form.treatment_type === type.value ? `${type.color} border-current` : "border-gray-200 hover:border-gray-300 bg-white")}>
                                      <p className="text-xs font-bold">{type.label}</p>
                                    </button>
                                  ))}
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                  <div className="col-span-2">
                                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Acción a realizar *</label>
                                    <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                                      className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm" />
                                  </div>
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Responsable</label>
                                    <input value={form.owner_name} onChange={e => setForm(f => ({ ...f, owner_name: e.target.value }))}
                                      className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm" />
                                  </div>
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Fecha límite</label>
                                    <input type="date" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
                                      className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm" />
                                  </div>
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Prioridad</label>
                                    <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                                      className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm">
                                      {Object.entries(PRIORITY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                                    </select>
                                  </div>
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Reducción esperada (%)</label>
                                    <input type="number" min={0} max={100} value={form.expected_risk_reduction}
                                      onChange={e => setForm(f => ({ ...f, expected_risk_reduction: e.target.value }))}
                                      className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm" />
                                  </div>
                                  <div className="col-span-2">
                                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Descripción</label>
                                    <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                                      rows={2} className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none" />
                                  </div>
                                </div>
                                <div className="flex justify-end">
                                  <button
                                    onClick={() => updateTreatmentMutation.mutate({
                                      id: t.id,
                                      data: {
                                        treatment_type: form.treatment_type,
                                        title: form.title,
                                        description: form.description || null,
                                        owner_name: form.owner_name || null,
                                        due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
                                        priority: form.priority,
                                        expected_risk_reduction: form.expected_risk_reduction ? Number(form.expected_risk_reduction) : null,
                                      }
                                    })}
                                    disabled={!form.title.trim() || updateTreatmentMutation.isPending}
                                    className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl px-5 py-2.5">
                                    {updateTreatmentMutation.isPending ? <><Loader size={13} className="animate-spin" /> Guardando…</> : "Guardar cambios"}
                                  </button>
                                </div>
                              </div>
                            );
                          }

                          const ttype = TREATMENT_TYPES.find(x => x.value === t.treatment_type);
                          return (
                            <div key={t.id} className={cn("flex items-start gap-3 border rounded-lg px-4 py-3 group relative", ttype?.color ?? "border-gray-200")}>
                              <div className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5">
                                <button onClick={() => {
                                  setAddingTo(null);
                                  setEditingTreatment(t.id);
                                  setForm({
                                    treatment_type: t.treatment_type,
                                    title: t.title,
                                    description: t.description || "",
                                    owner_name: t.owner_name || "",
                                    due_date: t.due_date ? new Date(t.due_date).toISOString().split('T')[0] : "",
                                    priority: t.priority,
                                    acceptance_justification: t.acceptance_justification || "",
                                    expected_risk_reduction: t.expected_risk_reduction ? String(t.expected_risk_reduction) : "",
                                  });
                                }} className="flex items-center gap-1 px-2 py-1 bg-white border border-gray-200 rounded-lg shadow-sm text-xs font-semibold text-green-700 hover:bg-green-50 transition-colors">
                                  Editar
                                </button>
                                <button onClick={() => {
                                  if (confirm("¿Estás seguro de que deseas eliminar este tratamiento?")) {
                                    deleteTreatmentMutation.mutate(t.id);
                                  }
                                }} className="flex items-center gap-1 px-2 py-1 bg-white border border-gray-200 rounded-lg shadow-sm text-xs font-semibold text-red-600 hover:bg-red-50 transition-colors">
                                  Borrar
                                </button>
                              </div>
                              <span className={cn("text-xs font-semibold px-2 py-0.5 rounded border flex-shrink-0 mt-0.5", ttype?.color)}>
                                {ttype?.label ?? t.treatment_type}
                              </span>
                              <div className="flex-1 min-w-0 pr-24">
                                <p className="text-sm font-medium text-gray-900">{t.title}</p>
                                {t.description && <p className="text-xs text-gray-500 mt-0.5">{t.description}</p>}
                                <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                                  {t.owner_name && <span className="flex items-center gap-1"><User size={10} />{t.owner_name}</span>}
                                  {t.due_date && <span className="flex items-center gap-1"><Calendar size={10} />{format(new Date(t.due_date), "d MMM yyyy")}</span>}
                                  <span className={cn("px-1.5 rounded", {
                                    "bg-orange-50 text-orange-600": t.priority === "immediate",
                                    "bg-yellow-50 text-yellow-600": t.priority === "short_term",
                                    "bg-blue-50 text-blue-600": t.priority === "medium_term",
                                    "bg-gray-100 text-gray-500": t.priority === "long_term",
                                  })}>{PRIORITY_LABELS[t.priority]}</span>
                                  {t.expected_risk_reduction && <span>Reducción esperada: {t.expected_risk_reduction}%</span>}
                                </div>
                              </div>
                            </div>

                          );
                        })}
                      </div>
                    )}

                    {/* Add treatment form */}
                    {addingHere ? (
                      <div className="border border-blue-200 rounded-xl p-4 bg-blue-50/30 space-y-4">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-semibold text-gray-800">Nueva acción de tratamiento</p>
                          <button onClick={() => { setAddingTo(null); setEditingTreatment(null); setForm(BLANK_TREATMENT); }}>
                            <X size={15} className="text-gray-400 hover:text-gray-700" />
                          </button>
                        </div>

                        {/* Treatment type selector */}
                        <div className="grid grid-cols-4 gap-2">
                          {TREATMENT_TYPES.map(t => (
                            <button key={t.value} onClick={() => setForm(f => ({ ...f, treatment_type: t.value }))}
                              className={cn("p-3 rounded-lg border-2 text-center transition-all",
                                form.treatment_type === t.value ? `${t.color} border-current` : "border-gray-200 hover:border-gray-300 bg-white")}>
                              <p className="text-xs font-bold">{t.label}</p>
                              <p className="text-xs text-gray-400 mt-0.5 leading-tight">{t.desc}</p>
                            </button>
                          ))}
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-600 mb-1.5">Acción a realizar *</label>
                            <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                              placeholder="Ej: Implementar validación de inputs en el módulo de pagos"
                              className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500" />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1.5">Responsable</label>
                            <input value={form.owner_name} onChange={e => setForm(f => ({ ...f, owner_name: e.target.value }))}
                              placeholder="Nombre o equipo"
                              className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500" />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1.5">Fecha límite</label>
                            <input type="date" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
                              className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500" />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1.5">Prioridad</label>
                            <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                              className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500">
                              {Object.entries(PRIORITY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1.5">Reducción esperada (%)</label>
                            <input type="number" min={0} max={100} value={form.expected_risk_reduction}
                              onChange={e => setForm(f => ({ ...f, expected_risk_reduction: e.target.value }))}
                              placeholder="Ej: 70"
                              className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500" />
                          </div>
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-600 mb-1.5">Descripción</label>
                            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                              rows={2} placeholder="Detalles de la acción…"
                              className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none" />
                          </div>
                          {form.treatment_type === "accept" && (
                            <div className="col-span-2">
                              <label className="block text-xs font-medium text-gray-600 mb-1.5">Justificación de aceptación *</label>
                              <textarea value={form.acceptance_justification} onChange={e => setForm(f => ({ ...f, acceptance_justification: e.target.value }))}
                                rows={2} placeholder="¿Por qué se acepta este riesgo?"
                                className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none" />
                            </div>
                          )}
                        </div>

                        <div className="flex justify-end">
                          <button
                            onClick={() => addTreatmentMutation.mutate(risk.id)}
                            disabled={!form.title.trim() || addTreatmentMutation.isPending}
                            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl px-5 py-2.5">
                            {addTreatmentMutation.isPending ? <><Loader size={13} className="animate-spin" /> Guardando…</> : <><Plus size={13} /> Agregar acción</>}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {/* AI suggestion panel */}
                        {suggestingFor === risk.id && suggestions.length > 0 && (
                          <div className="border border-purple-200 rounded-xl p-4 bg-purple-50/40 space-y-3">
                            <div className="flex items-center justify-between">
                              <p className="text-sm font-semibold text-purple-800 flex items-center gap-1.5">
                                <Sparkles size={14} className="text-purple-500" />
                                Sugerencias de la IA — elige y guarda
                              </p>
                              <button onClick={() => { setSuggestingFor(null); setSuggestions([]); }}>
                                <X size={14} className="text-gray-400 hover:text-gray-700" />
                              </button>
                            </div>
                            <div className="space-y-2">
                              {suggestions.map((s: any, idx: number) => {
                                const ttype = TREATMENT_TYPES.find(t => t.value === s.treatment_type);
                                return (
                                  <div key={idx} className="bg-white border border-purple-100 rounded-lg px-4 py-3 flex items-start gap-3">
                                    <span className={cn("text-xs font-semibold px-2 py-0.5 rounded border flex-shrink-0 mt-0.5", ttype?.color ?? "bg-gray-100 text-gray-600 border-gray-200")}>
                                      {ttype?.label ?? s.treatment_type}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                      <p className="text-sm font-medium text-gray-900">{s.title}</p>
                                      {s.description && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{s.description}</p>}
                                      <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400">
                                        {s.owner_name && <span className="flex items-center gap-1"><User size={10}/>{s.owner_name}</span>}
                                        <span>{PRIORITY_LABELS[s.priority] ?? s.priority}</span>
                                        {s.expected_risk_reduction && <span>↓{s.expected_risk_reduction}%</span>}
                                      </div>
                                    </div>
                                    <button
                                      onClick={() => {
                                        setForm({
                                          treatment_type: s.treatment_type ?? "mitigate",
                                          title: s.title ?? "",
                                          description: s.description ?? "",
                                          owner_name: s.owner_name ?? "",
                                          due_date: "",
                                          priority: s.priority ?? "medium_term",
                                          acceptance_justification: "",
                                          expected_risk_reduction: s.expected_risk_reduction ? String(s.expected_risk_reduction) : "",
                                        });
                                        setSuggestingFor(null);
                                        setSuggestions([]);
                                        setAddingTo(risk.id);
                                        setExpandedRisk(risk.id);
                                      }}
                                      className="flex-shrink-0 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-3 py-1.5 rounded-lg transition-colors">
                                      Usar
                                    </button>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        <div className="flex items-center gap-3 flex-wrap">
                          <button onClick={() => { setAddingTo(risk.id); setEditingTreatment(null); setExpandedRisk(risk.id); setForm(BLANK_TREATMENT); setSuggestingFor(null); }}
                            className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors">
                            <Plus size={14} /> Agregar acción
                          </button>
                          <span className="text-gray-200">|</span>
                          <div className="flex items-center gap-2">
                            <select
                              value={aiProvider}
                              onChange={e => {
                                const sel = availableProviders.find(p => p.value === e.target.value);
                                setAiProvider(e.target.value);
                                setAiModel(sel?.model ?? "");
                              }}
                              className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-600 focus:outline-none focus:border-purple-400 max-w-[200px]">
                              {availableProviders.length > 0
                                ? availableProviders.map(p => (
                                    <option key={p.value} value={p.value}>
                                      {p.label}{p.model ? ` — ${p.model}` : ""}
                                    </option>
                                  ))
                                : DEFAULT_AI_PROVIDERS.map(p => (
                                    <option key={p.value} value={p.value}>{p.label}</option>
                                  ))
                              }
                            </select>
                            <button
                              onClick={() => { setSuggestions([]); suggestMutation.mutate(risk.id); }}
                              disabled={suggestMutation.isPending && suggestMutation.variables === risk.id}
                              className="flex items-center gap-1.5 text-sm text-purple-600 hover:text-purple-800 font-medium transition-colors disabled:opacity-50">
                              {suggestMutation.isPending && suggestMutation.variables === risk.id
                                ? <><Loader size={13} className="animate-spin" /> Generando…</>
                                : <><Sparkles size={13} /> Sugerir con IA</>}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
