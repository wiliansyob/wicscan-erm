"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useProjectStore } from "@/lib/project";
import {
  biaApi,
  type BusinessProcessIn,
  type BiaCalculateIn,
  type BusinessProcessWithBiaOut,
  type AssetProcessLinkOut,
  type AssetSimpleOut,
} from "@/lib/api/context";
import {
  TrendingUp, Plus, Loader, AlertTriangle, Trash2, X,
  ChevronDown, ChevronUp, Info, Link2, Unlink, Pencil, Server, Layers,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";

const CRITICALITY_LABELS: Record<string, { label: string; color: string }> = {
  critical:  { label: "Crítico",    color: "bg-red-100 text-red-700" },
  important: { label: "Importante", color: "bg-orange-100 text-orange-700" },
  support:   { label: "Soporte",    color: "bg-blue-100 text-blue-700" },
};

const REVENUE_LABELS: Record<string, string> = {
  "<20": "< 20%",
  "20-50": "20 – 50%",
  ">50": "> 50%",
};

type ProcessForm = BusinessProcessIn;
type BiaForm = BiaCalculateIn;

const EMPTY_PROCESS: ProcessForm = {
  name: "",
  owner_name: "",
  criticality: "important",
  revenue_dependency: "20-50",
  has_manual_alternative: false,
  contractual_commitments: false,
  notes: "",
};

const EMPTY_BIA: BiaForm = {
  num_staff_affected: 0,
  avg_salary_hour: 0,
  infra_cost_per_hour: 0,
  contractual_penalty_per_hour: 0,
  sla_at_risk_value: 0,
  hourly_revenue: 0,
  revenue_dependency_pct: 20,
  sn_active: false,
  sanction_amount: 0,
  annual_revenue: 0,
  mtpd_hours: 24,
  rto_hours: 8,
  rpo_hours: 4,
};

function formatEuros(n?: number | null) {
  if (n == null) return "—";
  return `€${n.toLocaleString("es-ES", { maximumFractionDigits: 0 })}`;
}

function ProcessModal({
  initial,
  initialBia,
  onSave,
  onClose,
  saving,
}: {
  initial?: ProcessForm;
  initialBia?: BiaForm;
  onSave: (p: ProcessForm, b: BiaForm) => void;
  onClose: () => void;
  saving: boolean;
}) {
  const [proc, setProc] = useState<ProcessForm>(initial ?? EMPTY_PROCESS);
  const [bia, setBia] = useState<BiaForm>(initialBia ?? EMPTY_BIA);
  const [step, setStep] = useState<"process" | "bia" | "guide">("process");

  const setP = (k: keyof ProcessForm, v: unknown) =>
    setProc((prev) => ({ ...prev, [k]: v }));
  const setB = (k: keyof BiaForm, v: unknown) =>
    setBia((prev) => ({ ...prev, [k]: v }));

  // Live preview I(t) using dynamic RPO/RTO/MTPD horizons
  const preview = (() => {
    const cd = ((bia.num_staff_affected ?? 0) * (bia.avg_salary_hour ?? 0)) + (bia.infra_cost_per_hour ?? 0) + (bia.contractual_penalty_per_hour ?? 0);
    const pi = (bia.hourly_revenue ?? 0) * ((bia.revenue_dependency_pct ?? 0) / 100) + (bia.sla_at_risk_value ?? 0);
    const sn = bia.sn_active ? (bia.sanction_amount ?? 0) : 0;
    const rpo = bia.rpo_hours ?? 4;
    const rto = bia.rto_hours ?? 8;
    const mtpd = bia.mtpd_hours ?? 24;
    return {
      irpo:  { val: cd * rpo  + pi * rpo  + sn, label: `I(RPO=${rpo}h)`  },
      irto:  { val: cd * rto  + pi * rto  + sn, label: `I(RTO=${rto}h)`  },
      imtpd: { val: cd * mtpd + pi * mtpd + sn, label: `I(MTPD=${mtpd}h)` },
    };
  })();

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">
            {step === "process" ? "Proceso crítico" : step === "bia" ? "Estimación BIA" : "Guía de campos"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-5">
          {/* Step tabs */}
          <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg">
            {(["process", "bia", "guide"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setStep(s)}
                className={cn(
                  "flex-1 text-xs font-semibold py-1.5 rounded-md transition-all",
                  step === s ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
                )}
              >
                {s === "process" ? "1. Proceso" : s === "bia" ? "2. Impacto económico" : "3. Guía"}
              </button>
            ))}
          </div>

          {step === "process" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Nombre del proceso *</label>
                <input
                  type="text"
                  value={proc.name}
                  onChange={(e) => setP("name", e.target.value)}
                  placeholder="Ej: Procesamiento de pagos"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Responsable</label>
                <input
                  type="text"
                  value={proc.owner_name ?? ""}
                  onChange={(e) => setP("owner_name", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Criticidad</label>
                  <select
                    value={proc.criticality}
                    onChange={(e) => setP("criticality", e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none"
                  >
                    <option value="critical">Crítico</option>
                    <option value="important">Importante</option>
                    <option value="support">Soporte</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Dependencia de ingresos</label>
                  <select
                    value={proc.revenue_dependency}
                    onChange={(e) => setP("revenue_dependency", e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none"
                  >
                    <option value="<20">&lt; 20%</option>
                    <option value="20-50">20 – 50%</option>
                    <option value=">50">&gt; 50%</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={proc.has_manual_alternative}
                    onChange={(e) => setP("has_manual_alternative", e.target.checked)}
                    className="rounded border-gray-300 text-blue-600"
                  />
                  <span className="text-sm text-gray-700">Alternativa manual disponible</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={proc.contractual_commitments}
                    onChange={(e) => setP("contractual_commitments", e.target.checked)}
                    className="rounded border-gray-300 text-blue-600"
                  />
                  <span className="text-sm text-gray-700">Compromisos contractuales</span>
                </label>
              </div>
            </div>
          )}

          {step === "guide" && (
            <div className="space-y-5 text-sm">
              <p className="text-xs text-gray-500 flex gap-1.5 items-start">
                <Info size={12} className="flex-shrink-0 mt-0.5 text-gray-400" />
                Referencia rápida de cada parámetro del modelo BIA.
              </p>

              {/* Pestaña 1 */}
              <div>
                <p className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">Pestaña 1 — Proceso</p>
                <div className="space-y-2">
                  {[
                    { campo: "Nombre", desc: "Identificador del proceso crítico (ej: Procesamiento de pagos)." },
                    { campo: "Responsable", desc: "Persona u área dueña del proceso." },
                    { campo: "Criticidad", desc: "Crítico = operaciones core sin tolerancia a caída; Importante = afecta ingresos o imagen; Soporte = auxiliar." },
                    { campo: "Dependencia de ingresos", desc: "Fracción de facturación global que genera este proceso: < 20%, 20–50% o > 50%." },
                    { campo: "Alternativa manual", desc: "¿Existe un procedimiento de contingencia que permita operar sin el sistema?" },
                    { campo: "Compromisos contractuales", desc: "¿Hay SLAs o penalizaciones contractuales si este proceso falla?" },
                  ].map(({ campo, desc }) => (
                    <div key={campo} className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs font-semibold text-gray-800">{campo}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pestaña 2 */}
              <div>
                <p className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">Pestaña 2 — Impacto económico</p>
                <div className="space-y-2">
                  {[
                    { campo: "Empleados afectados", desc: "Número de personas que quedan inoperativas mientras el proceso está caído." },
                    { campo: "Coste salarial/hora (€)", desc: "Salario medio por hora de esos empleados. Se multiplica por el nº de empleados para obtener el coste laboral directo." },
                    { campo: "Coste infraestructura/hora (€)", desc: "Coste operativo del sistema por hora parado: licencias, cloud, soporte técnico, etc." },
                    { campo: "Penalización SLA/hora (€)", desc: "Penalización contractual por cada hora de incumplimiento de acuerdos de nivel de servicio." },
                    { campo: "Ingresos/hora (€)", desc: "Facturación horaria media que genera este proceso cuando está operativo." },
                    { campo: "Dependencia ingresos (%)", desc: "Qué porcentaje de esos ingresos/hora depende directamente de este proceso (0–100). Ej: 20 = el proceso aporta el 20% de los ingresos." },
                    { campo: "Brecha de datos personales", desc: "Activa el componente de sanción normativa (RGPD/ENS). Introduce la estimación de sanción si aplica." },
                    { campo: "MTPD (h)", desc: "Maximum Tolerable Period of Disruption: tiempo máximo que la organización puede sobrevivir sin este proceso antes de consecuencias irreversibles." },
                    { campo: "RTO (h)", desc: "Recovery Time Objective: en cuántas horas debe restaurarse el servicio para cumplir compromisos." },
                    { campo: "RPO (h)", desc: "Recovery Point Objective: antigüedad máxima de los datos que se puede perder (ej: 4h = puedes perder los últimos 4h de datos)." },
                  ].map(({ campo, desc }) => (
                    <div key={campo} className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs font-semibold text-gray-800">{campo}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Fórmula */}
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                <p className="text-xs font-bold text-blue-700 mb-2">Fórmula del impacto</p>
                <p className="text-xs font-mono text-blue-800 mb-1">I(t) = CD(t) + PI(t) + SN</p>
                <div className="space-y-1 text-xs text-blue-700">
                  <p><span className="font-semibold">CD(t)</span> = (empleados × coste_salarial + infra + penalización_sla) × t</p>
                  <p><span className="font-semibold">PI(t)</span> = (ingresos × dependencia% / 100) × t</p>
                  <p><span className="font-semibold">SN</span> = sanción única si hay brecha de datos personales</p>
                </div>
              </div>
            </div>
          )}

          {step === "bia" && (
            <div className="space-y-5">
              <p className="text-xs text-gray-500 flex gap-1.5 items-start">
                <Info size={12} className="flex-shrink-0 mt-0.5 text-gray-400" />
                Los valores calculados por el backend (I(RPO), I(RTO), I(MTPD)) son solo lectura.
                Introduce aquí los parámetros de entrada.
              </p>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Empleados afectados</label>
                  <input type="number" min={0} value={bia.num_staff_affected ?? 0}
                    onChange={(e) => setB("num_staff_affected", Number(e.target.value))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Coste salarial/hora (€)</label>
                  <input type="number" min={0} value={bia.avg_salary_hour ?? 0}
                    onChange={(e) => setB("avg_salary_hour", Number(e.target.value))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Coste infraestructura/hora (€)</label>
                  <input type="number" min={0} value={bia.infra_cost_per_hour ?? 0}
                    onChange={(e) => setB("infra_cost_per_hour", Number(e.target.value))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Penalización SLA/hora (€)</label>
                  <input type="number" min={0} value={bia.contractual_penalty_per_hour ?? 0}
                    onChange={(e) => setB("contractual_penalty_per_hour", Number(e.target.value))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Ingresos/hora (€)</label>
                  <input type="number" min={0} value={bia.hourly_revenue ?? 0}
                    onChange={(e) => setB("hourly_revenue", Number(e.target.value))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Dependencia ingresos (%)</label>
                  <input type="number" min={0} max={100} value={bia.revenue_dependency_pct ?? 0}
                    onChange={(e) => setB("revenue_dependency_pct", Number(e.target.value))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
                </div>
              </div>

              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={bia.sn_active ?? false}
                    onChange={(e) => setB("sn_active", e.target.checked)}
                    className="rounded border-gray-300 text-blue-600" />
                  <span className="text-sm text-gray-700 font-medium">Implica brecha de datos personales (activa sanciones SN)</span>
                </label>
                {bia.sn_active && (
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Estimación sanción (€)</label>
                    <input type="number" min={0} value={bia.sanction_amount ?? 0}
                      onChange={(e) => setB("sanction_amount", Number(e.target.value))}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
                  </div>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3">
                {(["rpo_hours", "rto_hours", "mtpd_hours"] as const).map((k) => (
                  <div key={k}>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{k.toUpperCase().replace("_HOURS", "")} (h)</label>
                    <input type="number" min={0} value={bia[k] ?? 0}
                      onChange={(e) => setB(k, Number(e.target.value))}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
                  </div>
                ))}
              </div>

              {/* Live preview */}
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                <p className="text-xs font-semibold text-blue-700 mb-3">Vista previa I(t) = CD(t) + PI(t) + SN</p>
                <div className="grid grid-cols-3 gap-3 text-center">
                  {[preview.irpo, preview.irto, preview.imtpd].map((item) => (
                    <div key={item.label} className="bg-white rounded-lg p-3 border border-blue-100">
                      <p className="text-xs text-gray-500 mb-1">{item.label}</p>
                      <p className="text-sm font-bold text-red-600">{formatEuros(item.val)}</p>
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-blue-500 mt-2 text-center">
                  Cálculo definitivo lo realiza el backend (determinista).
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-between gap-3">
          {step === "process" ? (
            <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2">Cancelar</button>
          ) : (
            <button onClick={() => setStep(step === "guide" ? "bia" : "process")} className="text-sm text-gray-500 hover:text-gray-700 font-medium px-4 py-2">
              ← Atrás
            </button>
          )}
          {step === "process" && (
            <button
              onClick={() => setStep("bia")}
              disabled={!proc.name.trim()}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2 px-5 transition-all"
            >
              Siguiente →
            </button>
          )}
          {step === "bia" && (
            <button
              onClick={() => onSave(proc, bia)}
              disabled={saving}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2 px-5 transition-all"
            >
              {saving ? <Loader size={13} className="animate-spin" /> : null}
              Guardar proceso
            </button>
          )}
          {step === "guide" && (
            <button
              onClick={() => setStep("bia")}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl py-2 px-5 transition-all"
            >
              Ir a parámetros →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const CRITICALITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high:     "bg-orange-100 text-orange-700",
  medium:   "bg-yellow-100 text-yellow-700",
  low:      "bg-green-100 text-green-700",
};

function AssetLinksPanel({
  process,
  projectId,
}: {
  process: BusinessProcessWithBiaOut;
  projectId: string;
}) {
  const qc = useQueryClient();
  const [addMode, setAddMode] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [newWeight, setNewWeight] = useState(100);
  const [addError, setAddError] = useState<string | null>(null);
  const [editingAssetId, setEditingAssetId] = useState<string | null>(null);
  const [editWeight, setEditWeight] = useState(100);

  const { data: assetsData } = useQuery({
    queryKey: ["assets-simple", projectId],
    queryFn: () => biaApi.listAssets(projectId).then((r) => r.data.items),
  });

  const linkedIds = new Set(process.asset_links.map((l) => l.asset_id));
  const availableAssets = (assetsData ?? []).filter((a) => !linkedIds.has(a.id));

  const upsertMutation = useMutation({
    mutationFn: ({ assetId, weight }: { assetId: string; weight: number }) =>
      biaApi.upsertAssetLink(process.id, assetId, weight / 100),
    onSuccess: (_, vars) => {
      if (vars.assetId === selectedAssetId) {
        setAddMode(false);
        setSelectedAssetId("");
        setNewWeight(100);
        setAddError(null);
      }
      setEditingAssetId(null);
      qc.invalidateQueries({ queryKey: ["bia-processes", projectId] });
    },
    onError: (err: any) =>
      setAddError(err?.response?.data?.detail ?? "Error al guardar."),
  });

  const removeMutation = useMutation({
    mutationFn: (assetId: string) => biaApi.removeAssetLink(process.id, assetId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bia-processes", projectId] }),
  });

  const totalWeight = process.asset_links.reduce((s, l) => s + l.weight, 0);

  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-600">
          <Link2 size={12} />
          Activos que soportan este proceso
        </div>
        {!addMode && availableAssets.length > 0 && (
          <button
            onClick={() => setAddMode(true)}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            <Plus size={11} /> Añadir activo
          </button>
        )}
      </div>

      {process.asset_links.length === 0 && !addMode && (
        <p className="text-xs text-gray-400 italic">
          Sin activos vinculados — el mapeo usará el proceso más crítico del proyecto como fallback.
        </p>
      )}

      {process.asset_links.length > 0 && (
        <ul className="space-y-1.5 mb-2">
          {process.asset_links.map((link) => (
            <li
              key={link.asset_id}
              className="flex items-center gap-3 bg-white border border-gray-100 rounded-lg px-3 py-2"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-800 truncate">
                    {link.asset_name ?? link.asset_id}
                  </span>
                  {link.asset_criticality && (
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0",
                      CRITICALITY_COLORS[link.asset_criticality] ?? "bg-gray-100 text-gray-600"
                    )}>
                      {link.asset_criticality}
                    </span>
                  )}
                  {link.asset_type && (
                    <span className="text-[10px] text-gray-400">{link.asset_type}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {editingAssetId === link.asset_id ? (
                  <>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={editWeight}
                      onChange={(e) => setEditWeight(Number(e.target.value))}
                      className="w-14 border border-blue-300 rounded px-1.5 py-0.5 text-xs text-center focus:outline-none"
                      autoFocus
                    />
                    <span className="text-xs text-gray-500">%</span>
                    <button
                      onClick={() => upsertMutation.mutate({ assetId: link.asset_id, weight: editWeight })}
                      disabled={upsertMutation.isPending}
                      className="text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-2 py-0.5 rounded transition-colors disabled:opacity-50"
                    >
                      {upsertMutation.isPending ? <Loader size={10} className="animate-spin" /> : "Guardar"}
                    </button>
                    <button
                      onClick={() => setEditingAssetId(null)}
                      className="text-[10px] text-gray-400 hover:text-gray-600 px-1"
                    >
                      ✕
                    </button>
                  </>
                ) : (
                  <>
                    <div className="text-center min-w-[40px]">
                      <p className="text-[10px] text-gray-400">Peso</p>
                      <p className="text-xs font-bold text-indigo-700">{Math.round(link.weight * 100)}%</p>
                    </div>
                    <button
                      onClick={() => { setEditingAssetId(link.asset_id); setEditWeight(Math.round(link.weight * 100)); }}
                      title="Editar peso"
                      className="flex items-center gap-1 text-[10px] text-gray-400 hover:text-blue-600 hover:bg-blue-50 px-1.5 py-1 rounded transition-colors"
                    >
                      <Pencil size={10} /> Editar
                    </button>
                    <button
                      onClick={() => { if (confirm(`¿Desvincular "${link.asset_name}"?`)) removeMutation.mutate(link.asset_id); }}
                      disabled={removeMutation.isPending}
                      title="Desvincular activo"
                      className="flex items-center gap-1 text-[10px] text-gray-400 hover:text-red-600 hover:bg-red-50 px-1.5 py-1 rounded transition-colors"
                    >
                      {removeMutation.isPending ? <Loader size={10} className="animate-spin" /> : <><Unlink size={10} /> Quitar</>}
                    </button>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {addMode && (
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 space-y-2">
          <div className="flex gap-2">
            <select
              value={selectedAssetId}
              onChange={(e) => setSelectedAssetId(e.target.value)}
              className="flex-1 border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-blue-500 bg-white"
            >
              <option value="">— Seleccionar activo —</option>
              {availableAssets.map((a) => (
                <option key={a.id} value={a.id}>{a.name} ({a.asset_type})</option>
              ))}
            </select>
            <div className="flex items-center gap-1 flex-shrink-0">
              <input
                type="number" min={1} max={100} value={newWeight}
                onChange={(e) => setNewWeight(Number(e.target.value))}
                className="w-16 border border-gray-200 rounded-lg px-2 py-1.5 text-xs text-center focus:outline-none focus:border-blue-500 bg-white"
              />
              <span className="text-xs text-gray-500">%</span>
            </div>
          </div>
          {addError && <p className="text-xs text-red-600">{addError}</p>}
          <div className="flex gap-2 justify-end">
            <button onClick={() => { setAddMode(false); setAddError(null); }}
              className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1">
              Cancelar
            </button>
            <button
              onClick={() => upsertMutation.mutate({ assetId: selectedAssetId, weight: newWeight })}
              disabled={!selectedAssetId || upsertMutation.isPending}
              className="flex items-center gap-1 text-xs bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-semibold px-3 py-1.5 rounded-lg transition-all"
            >
              {upsertMutation.isPending ? <Loader size={11} className="animate-spin" /> : <Link2 size={11} />}
              Vincular
            </button>
          </div>
        </div>
      )}

      {process.asset_links.length > 0 && (
        <p className="text-[10px] text-gray-400 mt-1.5">
          Suma de pesos: {Math.round(totalWeight * 100)}%
          {totalWeight > 1.01 && (
            <span className="text-amber-600 ml-1">⚠ supera 100% — revisa los pesos</span>
          )}
        </p>
      )}
    </div>
  );
}

function biaFormFromProcess(proc: BusinessProcessWithBiaOut): BiaForm {
  const params = (proc.bia?.breakdown as any)?.params ?? {};
  return {
    num_staff_affected: params.num_staff_affected ?? 0,
    avg_salary_hour: params.avg_salary_hour ?? 0,
    infra_cost_per_hour: params.infra_cost_per_hour ?? 0,
    contractual_penalty_per_hour: params.contractual_penalty_per_hour ?? 0,
    sla_at_risk_value: params.sla_at_risk_value ?? 0,
    hourly_revenue: params.hourly_revenue ?? 0,
    revenue_dependency_pct: params.revenue_dependency_pct ?? 20,
    sn_active: proc.bia?.sn_active ?? params.sn_active ?? false,
    sanction_amount: params.sanction_amount ?? 0,
    annual_revenue: params.annual_revenue ?? 0,
    // Read directly from bia root fields first (params may be missing these in old records)
    mtpd_hours: (proc.bia as any)?.mtpd_hours ?? params.mtpd_hours ?? 24,
    rto_hours: (proc.bia as any)?.rto_hours ?? params.rto_hours ?? 8,
    rpo_hours: (proc.bia as any)?.rpo_hours ?? params.rpo_hours ?? 4,
  };
}

export default function BiaPage() {
  const qc = useQueryClient();
  const { project } = useProjectStore();
  const projectId = project?.id;

  const [showModal, setShowModal] = useState(false);
  const [editTarget, setEditTarget] = useState<BusinessProcessWithBiaOut | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  async function handleExport() {
    if (!projectId) return;
    setExporting(true);
    setExportError(null);
    try {
      await biaApi.exportExcel(projectId, project.name);
    } catch (err: any) {
      setExportError(err?.message ?? "Error al generar el Excel");
    } finally {
      setExporting(false);
    }
  }

  const { data: processes = [], isLoading } = useQuery<BusinessProcessWithBiaOut[]>({
    queryKey: ["bia-processes", projectId],
    queryFn: () => biaApi.listProcesses(projectId!).then((r) => r.data),
    enabled: !!projectId,
  });

  const createMutation = useMutation({
    mutationFn: async ({ proc, bia }: { proc: BusinessProcessIn; bia: BiaCalculateIn }) => {
      const pRes = await biaApi.createProcess(projectId!, proc);
      const processId = pRes.data.id;
      await biaApi.calculateBia(processId, bia);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bia-processes", projectId] });
      setShowModal(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ proc, bia }: { proc: BusinessProcessIn; bia: BiaCalculateIn }) => {
      await biaApi.updateProcess(editTarget!.id, proc);
      await biaApi.calculateBia(editTarget!.id, bia);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bia-processes", projectId] });
      setEditTarget(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (processId: string) => biaApi.deleteProcess(processId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bia-processes", projectId] }),
  });

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <TrendingUp size={36} className="text-gray-300 mb-3" />
        <p className="text-gray-500 font-medium">Selecciona un proyecto primero</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-blue-600 mb-1">{project.name}</p>
          <h1 className="text-2xl font-bold text-gray-900">Business Impact Analysis</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Cuantifica el impacto económico por interrupción de cada proceso crítico.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {processes.length > 0 && (
            <button
              onClick={handleExport}
              disabled={exporting}
              title="Exportar Tablas 11, 12, 15 y 16 del TFM (BIA + Vulnerabilidades)"
              className="flex items-center gap-2 border border-gray-200 hover:border-green-400 bg-white hover:bg-green-50 text-gray-700 hover:text-green-700 text-sm font-medium rounded-xl py-2.5 px-4 transition-all disabled:opacity-50"
            >
              {exporting ? (
                <Loader size={14} className="animate-spin" />
              ) : (
                <Download size={14} />
              )}
              {exporting ? "Generando…" : "Exportar Excel"}
            </button>
          )}
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl py-2.5 px-4 transition-all"
          >
            <Plus size={15} /> Añadir proceso
          </button>
        </div>
      </div>

      {/* Export error */}
      {exportError && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          <AlertTriangle size={14} className="flex-shrink-0" />
          {exportError}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-16 gap-3 text-gray-500">
          <Loader size={18} className="animate-spin text-blue-600" />
          <span className="text-sm">Cargando procesos…</span>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && processes.length === 0 && (
        <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-10 text-center">
          <TrendingUp size={28} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 text-sm font-medium">Sin procesos registrados</p>
          <p className="text-gray-400 text-xs mt-1">
            Añade los procesos críticos de negocio para calcular su impacto económico.
          </p>
        </div>
      )}

      {/* Process list */}
      {processes.length > 0 && (
        <div className="space-y-3">
          {processes.map((proc) => {
            const bia = proc.bia;
            const crit = CRITICALITY_LABELS[proc.criticality];
            const isExpanded = expandedId === proc.id;

            let valRpo = 0, valRto = 0, valMtpd = 0;
            let rpo = 4, rto = 8, mtpd = 24;
            if (bia) {
              const bForm = biaFormFromProcess(proc);
              const cd = ((bForm.num_staff_affected ?? 0) * (bForm.avg_salary_hour ?? 0)) + (bForm.infra_cost_per_hour ?? 0) + (bForm.contractual_penalty_per_hour ?? 0);
              const pi = (bForm.hourly_revenue ?? 0) * ((bForm.revenue_dependency_pct ?? 0) / 100) + (bForm.sla_at_risk_value ?? 0);
              const sn = bForm.sn_active ? (bForm.sanction_amount ?? 0) : 0;
              rpo = bForm.rpo_hours ?? 4;
              rto = bForm.rto_hours ?? 8;
              mtpd = bForm.mtpd_hours ?? 24;
              valRpo = cd * rpo + pi * rpo + sn;
              valRto = cd * rto + pi * rto + sn;
              valMtpd = cd * mtpd + pi * mtpd + sn;
            }

            return (
              <div key={proc.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                {/* Row */}
                <div
                  className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : proc.id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="text-sm font-semibold text-gray-900 truncate">{proc.name}</p>
                      {crit && (
                        <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0", crit.color)}>
                          {crit.label}
                        </span>
                      )}
                    </div>
                    {proc.owner_name && (
                      <p className="text-xs text-gray-400">{proc.owner_name}</p>
                    )}
                  </div>

                  {/* Inline Assets display */}
                  <div className="hidden lg:flex items-center gap-1.5 flex-1 min-w-0 mr-4">
                    {proc.asset_links.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 overflow-hidden h-[22px]">
                        {proc.asset_links.map((link) => (
                          <span key={link.asset_id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-100 text-[10px] font-medium truncate max-w-[150px]" title={link.asset_name ?? undefined}>
                            <Layers size={10} className="text-blue-500 opacity-70" />
                            <span className="truncate">{link.asset_name}</span>
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-[10px] text-gray-300 italic flex items-center gap-1">
                        <Link2 size={10} /> Sin activos vinculados
                      </span>
                    )}
                  </div>

                  {bia ? (
                    <div className="flex items-center gap-6 flex-shrink-0">
                      {[
                        { label: `I(RPO=${rpo}h)`,  val: valRpo },
                        { label: `I(RTO=${rto}h)`,  val: valRto },
                        { label: `I(MTPD=${mtpd}h)`, val: valMtpd },
                      ].map((item) => (
                        <div key={item.label} className="text-center">
                          <p className="text-[10px] text-gray-400">{item.label}</p>
                          <p className="text-sm font-bold text-red-600">{formatEuros(item.val)}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-100">
                      Sin BIA
                    </span>
                  )}

                  <div className="flex items-center gap-2 ml-2">
                    {isExpanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                  </div>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="px-5 pb-4 pt-1 border-t border-gray-100 bg-gray-50/60">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm mb-4">
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">Dependencia ingresos</p>
                        <p className="font-medium text-gray-700">{REVENUE_LABELS[proc.revenue_dependency] ?? proc.revenue_dependency}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">Alternativa manual</p>
                        <p className="font-medium text-gray-700">{proc.has_manual_alternative ? "Sí" : "No"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">Compromisos contractuales</p>
                        <p className="font-medium text-gray-700">{proc.contractual_commitments ? "Sí" : "No"}</p>
                      </div>
                      {bia && (
                        <>
                          <div>
                            <p className="text-xs text-gray-400 mb-0.5">RPO / RTO / MTPD</p>
                            <p className="font-medium text-gray-700">
                              {bia.rpo_hours ?? "—"}h / {bia.rto_hours ?? "—"}h / {bia.mtpd_hours ?? "—"}h
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-400 mb-0.5">Brecha de datos</p>
                            <p className="font-medium text-gray-700">{bia.sn_active ? "Sí" : "No"}</p>
                          </div>
                        </>
                      )}
                    </div>

                    <AssetLinksPanel process={proc} projectId={projectId!} />

                    <div className="flex justify-end gap-2 mt-3">
                      <button
                        onClick={() => setEditTarget(proc)}
                        className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        <Pencil size={12} /> Editar
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`¿Eliminar el proceso "${proc.name}"?`)) {
                            deleteMutation.mutate(proc.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        <Trash2 size={12} /> Eliminar
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {createMutation.isError && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          <AlertTriangle size={14} className="flex-shrink-0" />
          {(createMutation.error as any)?.response?.data?.detail ?? "Error al guardar."}
        </div>
      )}

      {showModal && (
        <ProcessModal
          onSave={(proc, bia) => createMutation.mutate({ proc, bia })}
          onClose={() => setShowModal(false)}
          saving={createMutation.isPending}
        />
      )}

      {editTarget && (
        <ProcessModal
          initial={{
            name: editTarget.name,
            owner_name: editTarget.owner_name ?? "",
            criticality: editTarget.criticality,
            revenue_dependency: editTarget.revenue_dependency,
            has_manual_alternative: editTarget.has_manual_alternative,
            contractual_commitments: editTarget.contractual_commitments,
            notes: editTarget.notes ?? "",
          }}
          initialBia={biaFormFromProcess(editTarget)}
          onSave={(proc, bia) => updateMutation.mutate({ proc, bia })}
          onClose={() => setEditTarget(null)}
          saving={updateMutation.isPending}
        />
      )}
    </div>
  );
}
