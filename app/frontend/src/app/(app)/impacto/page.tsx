"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Zap, Save, CheckCircle2, AlertTriangle, ChevronDown, Clock,
  Building2, TrendingUp, Timer, Shield, Sparkles, Info,
} from "lucide-react";
import { useProjectStore } from "@/lib/project";
import { biaApi, BusinessProcessWithBiaOut } from "@/lib/api/context";
import { scenariosApi, RiskScenarioOut, ScenarioImpactUpdate } from "@/lib/api/assessment";
import { cn } from "@/lib/utils";

// ─── constants ────────────────────────────────────────────────────────────────

const PROB_COLOR: Record<number, string> = {
  1: "bg-green-100 text-green-700",
  2: "bg-blue-100 text-blue-700",
  3: "bg-yellow-100 text-yellow-700",
  4: "bg-orange-100 text-orange-700",
  5: "bg-red-100 text-red-700",
};

const IMPACT_COLOR: Record<number, string> = {
  1: "bg-green-100 text-green-700",
  2: "bg-blue-100 text-blue-700",
  3: "bg-yellow-100 text-yellow-700",
  4: "bg-orange-100 text-orange-700",
  5: "bg-red-100 text-red-700",
};

const RISK_SCORE_COLOR = (score: number) => {
  if (score >= 20) return "text-red-700 bg-red-50 border-red-200";
  if (score >= 12) return "text-orange-700 bg-orange-50 border-orange-200";
  if (score >= 6)  return "text-yellow-700 bg-yellow-50 border-yellow-200";
  return "text-green-700 bg-green-50 border-green-200";
};

const RISK_LABEL = (score: number) => {
  if (score >= 20) return "Crítico";
  if (score >= 12) return "Alto";
  if (score >= 6)  return "Medio";
  return "Bajo";
};

const DIMENSION_OPTIONS = ["Muy Alto", "Alto", "Medio", "Bajo", "Muy Bajo"] as const;
type DimensionLevel = typeof DIMENSION_OPTIONS[number];

const DIM_SCORE: Record<DimensionLevel, number> = {
  "Muy Alto": 5, "Alto": 4, "Medio": 3, "Bajo": 2, "Muy Bajo": 1,
};
const SCORE_DIM: Record<number, DimensionLevel> = {
  5: "Muy Alto", 4: "Alto", 3: "Medio", 2: "Bajo", 1: "Muy Bajo",
};
const SCORE_LEVEL: Record<number, string> = {
  5: "Muy Alto", 4: "Alto", 3: "Medio", 2: "Bajo", 1: "Muy Bajo",
};

const CRITICALITY_SCORE: Record<string, number> = {
  critical: 5, important: 4, support: 3, low: 2,
};
const CRITICALITY_LABEL: Record<string, { label: string; cls: string }> = {
  critical:  { label: "Crítico",    cls: "bg-red-100 text-red-700 border-red-200" },
  important: { label: "Importante", cls: "bg-orange-100 text-orange-700 border-orange-200" },
  support:   { label: "Soporte",    cls: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  low:       { label: "Bajo",       cls: "bg-green-100 text-green-700 border-green-200" },
};
const REVENUE_LABEL: Record<string, string> = {
  ">50":   ">50% de ingresos",
  "20-50": "20–50% de ingresos",
  "<20":   "<20% de ingresos",
};

// ─── helpers ─────────────────────────────────────────────────────────────────

function calcImpact(
  processCriticality: string,
  dims: Record<string, DimensionLevel | "">,
): number {
  const base = CRITICALITY_SCORE[processCriticality] ?? 3;
  const filled = Object.values(dims).filter(Boolean) as DimensionLevel[];
  if (filled.length === 0) return base;
  const avg = filled.reduce((s, d) => s + DIM_SCORE[d], 0) / filled.length;
  return Math.min(5, Math.max(base, Math.round(avg)));
}

function suggestDimensions(proc: BusinessProcessWithBiaOut): {
  operational: DimensionLevel;
  financial: DimensionLevel;
  normative: DimensionLevel;
  reputational: DimensionLevel;
} {
  const critScore = CRITICALITY_SCORE[proc.criticality] ?? 3;

  // Operational: driven by criticality + manual alternative
  const opScore = proc.has_manual_alternative ? Math.max(1, critScore - 1) : critScore;

  // Financial: driven by revenue dependency + BIA 24h impact
  let fiScore = critScore;
  if (proc.revenue_dependency === ">50") fiScore = 5;
  else if (proc.revenue_dependency === "20-50") fiScore = Math.max(fiScore, 4);
  else if (proc.revenue_dependency === "<20") fiScore = Math.min(fiScore, 3);
  // BIA 24h: >50k€ bumps up
  if (proc.bia?.impact_24h && proc.bia.impact_24h > 50000) fiScore = Math.min(5, fiScore + 1);

  // Normative: driven by sn_active + contractual commitments
  let noScore = 1;
  if (proc.bia?.sn_active) noScore = Math.max(noScore, 4);
  if (proc.contractual_commitments) noScore = Math.max(noScore, 3);

  // Reputational: driven by criticality + revenue dependency
  const reScore = proc.revenue_dependency === ">50" ? Math.min(5, critScore) : Math.max(1, critScore - 1);

  return {
    operational:  SCORE_DIM[Math.min(5, Math.max(1, opScore))],
    financial:    SCORE_DIM[Math.min(5, Math.max(1, fiScore))],
    normative:    SCORE_DIM[Math.min(5, Math.max(1, noScore))],
    reputational: SCORE_DIM[Math.min(5, Math.max(1, reScore))],
  };
}

// ─── sub-components ───────────────────────────────────────────────────────────

function DimensionSelect({
  label,
  value,
  onChange,
  suggested,
}: {
  label: string;
  value: DimensionLevel | "";
  onChange: (v: DimensionLevel | "") => void;
  suggested?: DimensionLevel;
}) {
  const DIM_BG: Record<DimensionLevel, string> = {
    "Muy Alto": "text-red-700 bg-red-50",
    "Alto":     "text-orange-700 bg-orange-50",
    "Medio":    "text-yellow-700 bg-yellow-50",
    "Bajo":     "text-blue-700 bg-blue-50",
    "Muy Bajo": "text-green-700 bg-green-50",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-medium text-gray-600">{label}</label>
        {suggested && !value && (
          <button
            onClick={() => onChange(suggested)}
            className="text-[10px] text-indigo-500 hover:text-indigo-700"
          >
            Sug: {suggested}
          </button>
        )}
      </div>
      <div className="relative">
        <select
          value={value}
          onChange={e => onChange(e.target.value as DimensionLevel | "")}
          className={cn(
            "w-full appearance-none border rounded-lg px-3 py-2 text-sm pr-8 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
            value ? DIM_BG[value as DimensionLevel] + " border-transparent font-medium" : "bg-white border-gray-300 text-gray-700",
          )}
        >
          <option value="">— Sin asignar —</option>
          {DIMENSION_OPTIONS.map(o => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
        <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
      </div>
    </div>
  );
}

// ─── BIA context panel ────────────────────────────────────────────────────────

function BiaPanel({ proc }: { proc: BusinessProcessWithBiaOut }) {
  const bia = proc.bia;
  const crit = CRITICALITY_LABEL[proc.criticality] ?? { label: proc.criticality, cls: "bg-gray-100 text-gray-600 border-gray-200" };

  const fmtEur = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

  const regulations: string[] = [];
  if (bia?.sn_active) regulations.push("Sanciones normativas activas");
  if (proc.contractual_commitments) regulations.push("Compromisos contractuales");

  return (
    <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Building2 size={14} className="text-indigo-600" />
        <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">
          Contexto BIA — Proceso afectado
        </span>
      </div>

      {/* Process name + criticality */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-semibold text-gray-800">{proc.name}</span>
        <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", crit.cls)}>
          {crit.label}
        </span>
        {proc.has_manual_alternative && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 border border-green-200">
            Alternativa manual disponible
          </span>
        )}
      </div>

      {/* BIA metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Revenue dependency */}
        <div className="bg-white rounded-lg p-2.5 border border-indigo-100">
          <div className="flex items-center gap-1 text-[10px] text-gray-500 mb-0.5">
            <TrendingUp size={10} /> Dependencia ingresos
          </div>
          <p className="text-sm font-bold text-gray-800">
            {REVENUE_LABEL[proc.revenue_dependency] ?? proc.revenue_dependency}
          </p>
        </div>

        {/* RTO */}
        {bia?.rto_hours != null && (
          <div className="bg-white rounded-lg p-2.5 border border-indigo-100">
            <div className="flex items-center gap-1 text-[10px] text-gray-500 mb-0.5">
              <Timer size={10} /> RTO objetivo
            </div>
            <p className="text-sm font-bold text-gray-800">{bia.rto_hours}h</p>
          </div>
        )}

        {/* Impact 24h */}
        {bia?.impact_24h != null && (
          <div className={cn(
            "rounded-lg p-2.5 border",
            bia.impact_24h > 50000
              ? "bg-red-50 border-red-200"
              : bia.impact_24h > 10000
              ? "bg-orange-50 border-orange-200"
              : "bg-white border-indigo-100",
          )}>
            <div className="flex items-center gap-1 text-[10px] text-gray-500 mb-0.5">
              <Zap size={10} /> Pérdida estimada 24h
            </div>
            <p className={cn(
              "text-sm font-bold",
              bia.impact_24h > 50000 ? "text-red-700" : bia.impact_24h > 10000 ? "text-orange-700" : "text-gray-800",
            )}>
              {fmtEur(bia.impact_24h)}
            </p>
          </div>
        )}

        {/* RPO */}
        {bia?.rpo_hours != null && (
          <div className="bg-white rounded-lg p-2.5 border border-indigo-100">
            <div className="flex items-center gap-1 text-[10px] text-gray-500 mb-0.5">
              <Timer size={10} /> RPO máximo
            </div>
            <p className="text-sm font-bold text-gray-800">{bia.rpo_hours}h</p>
          </div>
        )}
      </div>

      {/* Regulations */}
      {regulations.length > 0 && (
        <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <Shield size={13} className="text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-amber-700">Obligaciones regulatorias</p>
            <p className="text-xs text-amber-600">{regulations.join(" · ")}</p>
          </div>
        </div>
      )}

      {/* Assets linked */}
      {proc.asset_links && proc.asset_links.length > 0 && (
        <div className="text-xs text-indigo-500">
          Activos que soportan este proceso:{" "}
          <span className="font-medium text-indigo-700">
            {proc.asset_links.map(a => a.asset_name ?? a.asset_id).join(", ")}
          </span>
        </div>
      )}
    </div>
  );
}

// ─── ScenarioImpactCard ───────────────────────────────────────────────────────

interface ImpactFormState {
  process_id: string;
  impact_operational: DimensionLevel | "";
  impact_financial: DimensionLevel | "";
  impact_normative: DimensionLevel | "";
  impact_reputational: DimensionLevel | "";
}

function ScenarioImpactCard({
  scenario,
  processes,
}: {
  scenario: RiskScenarioOut;
  processes: BusinessProcessWithBiaOut[];
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<ImpactFormState>({
    process_id: scenario.business_process_id ?? "",
    impact_operational:  (scenario.impact_operational  as DimensionLevel | "") ?? "",
    impact_financial:    (scenario.impact_financial    as DimensionLevel | "") ?? "",
    impact_normative:    (scenario.impact_normative    as DimensionLevel | "") ?? "",
    impact_reputational: (scenario.impact_reputational as DimensionLevel | "") ?? "",
  });

  const selectedProcess = processes.find(p => p.id === form.process_id) ?? null;
  const suggestions = selectedProcess ? suggestDimensions(selectedProcess) : null;

  // Auto-apply BIA suggestions when process first selected and no dims set yet
  useEffect(() => {
    if (!selectedProcess || !suggestions) return;
    const anyFilled = form.impact_operational || form.impact_financial || form.impact_normative || form.impact_reputational;
    if (!anyFilled) {
      setForm(f => ({
        ...f,
        impact_operational:  suggestions.operational,
        impact_financial:    suggestions.financial,
        impact_normative:    suggestions.normative,
        impact_reputational: suggestions.reputational,
      }));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.process_id]);

  const dims = {
    op: form.impact_operational,
    fi: form.impact_financial,
    no: form.impact_normative,
    re: form.impact_reputational,
  };
  const derivedImpact = selectedProcess
    ? calcImpact(selectedProcess.criticality, dims)
    : null;

  const riskScore = scenario.probability != null && derivedImpact != null
    ? scenario.probability * derivedImpact
    : null;

  const saveMut = useMutation({
    mutationFn: (data: ScenarioImpactUpdate) =>
      scenariosApi.updateImpacto(scenario.id, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenarios"] }),
  });

  const handleSave = () => {
    if (!form.process_id || derivedImpact == null) return;
    saveMut.mutate({
      business_process_id: form.process_id,
      impact: derivedImpact,
      impact_level: SCORE_LEVEL[derivedImpact] ?? "Medio",
      impact_rationale: null,
      impact_operational:  form.impact_operational  || null,
      impact_financial:    form.impact_financial    || null,
      impact_normative:    form.impact_normative    || null,
      impact_reputational: form.impact_reputational || null,
    });
  };

  const applySuggestions = () => {
    if (!suggestions) return;
    setForm(f => ({
      ...f,
      impact_operational:  suggestions.operational,
      impact_financial:    suggestions.financial,
      impact_normative:    suggestions.normative,
      impact_reputational: suggestions.reputational,
    }));
  };

  const isComplete = scenario.status === "impact_assessed" || scenario.status === "risk_generated";
  const allDimsFilled = form.impact_operational && form.impact_financial && form.impact_normative && form.impact_reputational;

  return (
    <div className={cn(
      "bg-white border rounded-xl shadow-sm overflow-hidden",
      isComplete ? "border-green-300" : "border-gray-200",
    )}>
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        <span className="text-xs font-bold text-indigo-600 w-14 flex-shrink-0">
          {scenario.scenario_code}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800 truncate">
            {scenario.title || scenario.consequence}
          </p>
          {scenario.finding_count != null && (
            <p className="text-xs text-gray-400">{scenario.finding_count} hallazgos</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {scenario.probability != null && (
            <span className={cn("text-xs font-bold px-2 py-0.5 rounded-full", PROB_COLOR[scenario.probability])}>
              P{scenario.probability}
            </span>
          )}
          {derivedImpact != null ? (
            <span className={cn("text-xs font-bold px-2 py-0.5 rounded-full", IMPACT_COLOR[derivedImpact])}>
              I{derivedImpact}
            </span>
          ) : scenario.impact != null ? (
            <span className={cn("text-xs font-bold px-2 py-0.5 rounded-full", IMPACT_COLOR[scenario.impact])}>
              I{scenario.impact}
            </span>
          ) : (
            <span className="text-xs text-gray-400 flex items-center gap-1"><Clock size={11} /> Sin I</span>
          )}
          {isComplete && <CheckCircle2 size={14} className="text-green-500" />}
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Process selector */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Proceso de negocio afectado (BIA)
          </label>
          <div className="relative">
            <select
              value={form.process_id}
              onChange={e => setForm(f => ({ ...f, process_id: e.target.value }))}
              className="w-full appearance-none border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white pr-8 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">— Seleccionar proceso —</option>
              {processes.map(p => {
                const crit = CRITICALITY_LABEL[p.criticality];
                return (
                  <option key={p.id} value={p.id}>
                    {p.name} · {crit?.label ?? p.criticality} · {REVENUE_LABEL[p.revenue_dependency] ?? p.revenue_dependency}
                  </option>
                );
              })}
            </select>
            <ChevronDown size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* BIA context panel — only when process selected */}
        {selectedProcess && <BiaPanel proc={selectedProcess} />}

        {/* Suggestions bar */}
        {selectedProcess && suggestions && (
          <div className="flex items-center gap-3 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
            <Sparkles size={14} className="text-indigo-500 flex-shrink-0" />
            <div className="flex-1 text-xs text-indigo-700">
              <span className="font-semibold">Sugerencia basada en BIA: </span>
              Op: <strong>{suggestions.operational}</strong> ·
              Fi: <strong>{suggestions.financial}</strong> ·
              No: <strong>{suggestions.normative}</strong> ·
              Re: <strong>{suggestions.reputational}</strong>
            </div>
            <button
              onClick={applySuggestions}
              className="flex-shrink-0 text-xs bg-indigo-600 text-white px-3 py-1 rounded-lg hover:bg-indigo-700 font-medium"
            >
              Aplicar
            </button>
          </div>
        )}

        {/* Dimension selectors */}
        {selectedProcess && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <DimensionSelect
              label="Operacional"
              value={form.impact_operational}
              onChange={v => setForm(f => ({ ...f, impact_operational: v }))}
              suggested={suggestions?.operational}
            />
            <DimensionSelect
              label="Financiero"
              value={form.impact_financial}
              onChange={v => setForm(f => ({ ...f, impact_financial: v }))}
              suggested={suggestions?.financial}
            />
            <DimensionSelect
              label="Normativo"
              value={form.impact_normative}
              onChange={v => setForm(f => ({ ...f, impact_normative: v }))}
              suggested={suggestions?.normative}
            />
            <DimensionSelect
              label="Reputacional"
              value={form.impact_reputational}
              onChange={v => setForm(f => ({ ...f, impact_reputational: v }))}
              suggested={suggestions?.reputational}
            />
          </div>
        )}

        {/* Impact + risk score meter */}
        {selectedProcess && derivedImpact != null && (
          <div className={cn(
            "rounded-xl border p-4 space-y-3",
            riskScore != null && riskScore >= 20
              ? "bg-red-50 border-red-200"
              : riskScore != null && riskScore >= 12
              ? "bg-orange-50 border-orange-200"
              : "bg-gray-50 border-gray-200",
          )}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Impacto calculado</p>
                <p className="text-lg font-bold text-gray-900">
                  {derivedImpact}/5
                  <span className="text-sm font-normal text-gray-600 ml-1.5">
                    — {SCORE_LEVEL[derivedImpact]}
                  </span>
                </p>
              </div>
              {riskScore != null && (
                <div className="text-right">
                  <p className="text-xs text-gray-500 mb-0.5">Riesgo P×I</p>
                  <p className={cn(
                    "text-lg font-bold px-3 py-0.5 rounded-full border",
                    RISK_SCORE_COLOR(riskScore),
                  )}>
                    {riskScore}/25
                    <span className="text-xs font-semibold ml-1.5">{RISK_LABEL(riskScore)}</span>
                  </p>
                </div>
              )}
            </div>

            {/* Visual impact bar */}
            <div>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map(i => (
                  <div
                    key={i}
                    className={cn(
                      "h-2 flex-1 rounded-full transition-all",
                      i <= derivedImpact
                        ? derivedImpact >= 4 ? "bg-red-500" : derivedImpact === 3 ? "bg-yellow-400" : "bg-blue-400"
                        : "bg-gray-200",
                    )}
                  />
                ))}
              </div>
              <div className="flex justify-between text-[10px] text-gray-400 mt-0.5 px-0.5">
                <span>Muy Bajo</span><span>Bajo</span><span>Medio</span><span>Alto</span><span>Muy Alto</span>
              </div>
            </div>

            {!allDimsFilled && (
              <div className="flex items-center gap-1.5 text-xs text-amber-600">
                <Info size={11} />
                Asigna las 4 dimensiones para un cálculo más preciso
              </div>
            )}
          </div>
        )}

        {/* Save */}
        {selectedProcess && (
          <div className="flex items-center justify-between">
            {saveMut.isError && (
              <span className="flex items-center gap-1 text-xs text-red-600">
                <AlertTriangle size={12} /> Error al guardar
              </span>
            )}
            {saveMut.isSuccess && (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <CheckCircle2 size={12} /> Guardado
              </span>
            )}
            <div className="ml-auto">
              <button
                onClick={handleSave}
                disabled={!form.process_id || derivedImpact == null || saveMut.isPending}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40 font-medium"
              >
                {saveMut.isPending ? (
                  <span className="animate-spin h-3.5 w-3.5 border-2 border-white/50 border-t-white rounded-full" />
                ) : (
                  <Save size={13} />
                )}
                Guardar impacto
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── page ─────────────────────────────────────────────────────────────────────

export default function ImpactoPage() {
  const { project } = useProjectStore();

  const { data: scenarios, isLoading: loadingScenarios } = useQuery({
    queryKey: ["scenarios", project?.id],
    queryFn: () => scenariosApi.list(project!.id).then(r => r.data),
    enabled: !!project,
  });

  const { data: processesRaw } = useQuery({
    queryKey: ["bia-processes", project?.id],
    queryFn: () => biaApi.listProcesses(project!.id).then(r => r.data),
    enabled: !!project,
  });
  const processes: BusinessProcessWithBiaOut[] = (processesRaw as BusinessProcessWithBiaOut[] | undefined) ?? [];

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Selecciona un proyecto para continuar.
      </div>
    );
  }

  const total = scenarios?.length ?? 0;
  const done  = scenarios?.filter(s => s.impact != null).length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Zap size={22} className="text-indigo-600" /> Impacto
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Vincula cada escenario a un proceso de negocio y revisa el contexto BIA para asignar el impacto en las 4 dimensiones.
        </p>
      </div>

      {/* Progress */}
      {total > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl px-5 py-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1.5">
            <span>Escenarios con impacto asignado</span>
            <span className="font-semibold text-gray-700">{done}/{total}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all"
              style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}

      {/* List */}
      {loadingScenarios ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-48 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : total === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <Zap size={36} className="mx-auto mb-3 opacity-40" />
          <p className="font-medium">No hay escenarios</p>
          <p className="text-sm mt-1">
            Ve a <strong>Escenarios</strong> y analiza con IA primero.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {scenarios!.map(s => (
            <ScenarioImpactCard key={s.id} scenario={s} processes={processes} />
          ))}
        </div>
      )}

      {/* Done hint */}
      {done === total && total > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl px-5 py-4">
          <p className="text-sm text-indigo-700 font-semibold">
            Todos los escenarios tienen impacto asignado.
          </p>
          <p className="text-sm text-indigo-600 mt-0.5">
            Continúa en <strong>Riesgos</strong> para generar el registro completo P × I con narrativa ejecutiva.
          </p>
        </div>
      )}
    </div>
  );
}
