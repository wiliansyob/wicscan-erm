"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCw, ChevronDown, ChevronUp,
  CheckCircle2, Clock, Trash2, Loader,
  ShieldAlert, Code, Copy, Pencil, Check, X, AlertTriangle,
} from "lucide-react";
import { useProjectStore } from "@/lib/project";
import { findingsApi } from "@/lib/api";
import { scenariosApi, RiskScenarioOut, ScenarioFinding } from "@/lib/api/assessment";
import { cn } from "@/lib/utils";

// ─── constants ────────────────────────────────────────────────────────────────

const PROB_COLOR: Record<number, string> = {
  1: "bg-green-100 text-green-700 border-green-200",
  2: "bg-blue-100 text-blue-700 border-blue-200",
  3: "bg-yellow-100 text-yellow-700 border-yellow-200",
  4: "bg-orange-100 text-orange-700 border-orange-200",
  5: "bg-red-100 text-red-700 border-red-200",
};

const PROB_LEVEL: Record<number, string> = {
  1: "Muy Baja", 2: "Baja", 3: "Media", 4: "Alta", 5: "Muy Alta",
};

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:      "bg-blue-100 text-blue-700 border-blue-200",
  info:     "bg-gray-100 text-gray-500 border-gray-200",
};

const SCANNER_TAG: Record<string, { label: string; cls: string }> = {
  sonarqube:   { label: "SAST", cls: "bg-purple-100 text-purple-700 border-purple-200" },
  semgrep:     { label: "SAST", cls: "bg-purple-100 text-purple-700 border-purple-200" },
  bandit:      { label: "SAST", cls: "bg-purple-100 text-purple-700 border-purple-200" },
  checkmarx:   { label: "SAST", cls: "bg-purple-100 text-purple-700 border-purple-200" },
  zap:         { label: "DAST", cls: "bg-cyan-100 text-cyan-700 border-cyan-200" },
  "owasp-zap": { label: "DAST", cls: "bg-cyan-100 text-cyan-700 border-cyan-200" },
  nikto:       { label: "DAST", cls: "bg-cyan-100 text-cyan-700 border-cyan-200" },
  burp:        { label: "DAST", cls: "bg-cyan-100 text-cyan-700 border-cyan-200" },
  ai:          { label: "IA", cls: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  gpt:         { label: "IA", cls: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  gemini:      { label: "IA", cls: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  claude:      { label: "IA", cls: "bg-emerald-100 text-emerald-700 border-emerald-200" },
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  pending:         <Clock size={13} className="text-gray-400" />,
  prob_assessed:   <CheckCircle2 size={13} className="text-blue-500" />,
  impact_assessed: <CheckCircle2 size={13} className="text-green-500" />,
  risk_generated:  <CheckCircle2 size={13} className="text-purple-500" />,
};

function getScannerTag(scanner: string | null): { label: string; cls: string } | null {
  if (!scanner) return null;
  const key = scanner.toLowerCase();
  return (
    SCANNER_TAG[key] ??
    // prefix matching: "sonar" → SAST, etc.
    (key.includes("sonar") || key.includes("sast")
      ? { label: "SAST", cls: "bg-purple-100 text-purple-700 border-purple-200" }
      : key.includes("zap") || key.includes("dast") || key.includes("burp")
      ? { label: "DAST", cls: "bg-cyan-100 text-cyan-700 border-cyan-200" }
      : { label: scanner.toUpperCase().slice(0, 8), cls: "bg-gray-100 text-gray-600 border-gray-200" })
  );
}

// ─── FindingRow ───────────────────────────────────────────────────────────────

const FINDING_TYPE_LABEL: Record<string, string> = {
  vulnerability: "Vulnerabilidad",
  web:           "Web",
  infrastructure:"Infraestructura",
  code:          "Código",
  configuration: "Configuración",
  compliance:    "Cumplimiento",
  secret:        "Secreto expuesto",
  sca:           "Componente",
};

function FindingRow({ finding }: { finding: ScenarioFinding }) {
  const [showSnippet, setShowSnippet] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);

  const { data: snippetData, isLoading: snippetLoading } = useQuery({
    queryKey: ["finding-snippet", finding.id],
    queryFn: () => findingsApi.getSnippet(finding.id).then(r => r.data),
    enabled: showSnippet && !!finding.file_path,
  });

  const hasCode = !!finding.file_path;
  const tag = getScannerTag(finding.scanner);
  const desc = finding.description ?? "";
  const longDesc = desc.length > 180;
  const scannerDisplay = finding.scanner
    ? finding.scanner.charAt(0).toUpperCase() + finding.scanner.slice(1)
    : null;
  const confidencePct = finding.confidence != null
    ? Math.round(finding.confidence * 100)
    : null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="px-4 py-3 space-y-2">
        {/* Top row: severity + scanner tags + title */}
        <div className="flex items-start gap-2">
          <span className={cn(
            "text-xs px-1.5 py-0.5 rounded border font-semibold flex-shrink-0 mt-0.5 uppercase",
            SEV_BADGE[(finding.severity ?? "info").toLowerCase()] ?? SEV_BADGE.info,
          )}>
            {finding.severity ?? "info"}
          </span>

          {tag && (
            <span className={cn("text-xs px-1.5 py-0.5 rounded border font-bold flex-shrink-0 mt-0.5", tag.cls)}>
              {tag.label}
            </span>
          )}

          {finding.finding_type && (
            <span className="text-xs px-1.5 py-0.5 rounded border bg-gray-50 text-gray-600 border-gray-200 flex-shrink-0 mt-0.5">
              {FINDING_TYPE_LABEL[finding.finding_type] ?? finding.finding_type}
            </span>
          )}

          <p className="text-sm font-medium text-gray-800 flex-1">{finding.title}</p>

          {hasCode && (
            <button
              onClick={() => setShowSnippet(v => !v)}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 flex-shrink-0"
            >
              <Code size={12} />
              {showSnippet ? "Ocultar" : "Ver código"}
            </button>
          )}
        </div>

        {/* Technical metadata row */}
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500">
          {finding.cwe && (
            <span className="font-mono font-medium text-gray-700">CWE-{finding.cwe.replace(/^CWE-/i, "")}</span>
          )}
          {finding.owasp_category && (
            <span>{finding.owasp_category}</span>
          )}
          {finding.category && !finding.owasp_category && (
            <span>{finding.category}</span>
          )}
          {finding.asset_name && (
            <span className="text-indigo-600 font-medium">{finding.asset_name}</span>
          )}
          {scannerDisplay && (
            <span className="text-gray-400">
              Detectado por: <span className="text-gray-600">{scannerDisplay}</span>
            </span>
          )}
          {confidencePct != null && (
            <span className="text-gray-400">
              Confianza: <span className="text-gray-600">{confidencePct}%</span>
            </span>
          )}
        </div>

        {/* File location (SAST) */}
        {finding.file_path && (
          <p className="text-xs text-gray-400 font-mono bg-gray-50 px-2 py-1 rounded">
            📄 {finding.file_path}
            {finding.line_start ? <span className="text-orange-500">:{finding.line_start}</span> : ""}
          </p>
        )}

        {/* Description — full text, expandable if long */}
        {desc && (
          <div>
            <p className={cn(
              "text-xs text-gray-700 leading-relaxed",
              !descExpanded && longDesc && "line-clamp-3",
            )}>
              {desc}
            </p>
            {longDesc && (
              <button
                onClick={() => setDescExpanded(v => !v)}
                className="text-xs text-blue-500 hover:text-blue-700 mt-0.5"
              >
                {descExpanded ? "Mostrar menos ▲" : "Mostrar más ▼"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Code snippet panel */}
      {showSnippet && (
        <div className="border-t border-gray-100 bg-gray-50 px-4 pb-3 pt-2">
          {snippetLoading ? (
            <div className="text-xs text-gray-400 py-3 text-center">
              <Loader size={12} className="animate-spin inline mr-1" /> Cargando fragmento…
            </div>
          ) : snippetData?.snippet?.length > 0 ? (
            <div className="space-y-2">
              <div className="bg-gray-900 rounded-lg overflow-hidden text-xs text-gray-300 font-mono overflow-x-auto">
                {snippetData.snippet.map((line: any, i: number) => (
                  <div
                    key={i}
                    className={cn(
                      "px-3 py-0.5 whitespace-pre",
                      line.line === finding.line_start
                        ? "bg-red-900/40 text-red-100 border-l-2 border-red-500"
                        : "hover:bg-gray-800",
                    )}
                  >
                    <span className="inline-block w-8 text-gray-600 select-none">{line.line}</span>
                    {line.code}
                  </div>
                ))}
              </div>
              <button
                onClick={() => {
                  const codeStr = snippetData.snippet
                    .map((l: any) => `${l.line}: ${l.code}`)
                    .join("\n");
                  const prompt = `Actúa como experto en ciberseguridad. Corrige esta vulnerabilidad:\n\nTítulo: ${finding.title}\nArchivo: ${finding.file_path}\n\nCódigo:\n\`\`\`\n${codeStr}\n\`\`\`\n\n¿Qué cambios exactos debo aplicar?`;
                  navigator.clipboard.writeText(prompt);
                }}
                className="w-full flex items-center justify-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium py-1.5 rounded-lg"
              >
                <Copy size={11} /> Copiar prompt de remediación
              </button>
            </div>
          ) : (
            <p className="text-xs text-gray-400 py-2 text-center">No hay fragmento de código disponible.</p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── ProbabilityEditor ────────────────────────────────────────────────────────

function ProbabilityEditor({
  scenario,
  onUpdated,
}: {
  scenario: RiskScenarioOut;
  onUpdated: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState<number>(scenario.probability ?? 3);

  const mut = useMutation({
    mutationFn: (v: number) =>
      scenariosApi
        .updateProbabilidad(scenario.id, {
          probability: v,
          prob_level: PROB_LEVEL[v] ?? "Media",
          probability_rationale: scenario.probability_rationale ?? undefined,
        })
        .then(r => r.data),
    onSuccess: () => {
      setEditing(false);
      onUpdated();
    },
  });

  if (!editing) {
    return scenario.probability == null ? (
      <button
        onClick={() => setEditing(true)}
        className="text-xs text-gray-400 italic hover:text-blue-500 flex items-center gap-1 px-2 py-0.5 rounded border border-dashed border-gray-300 hover:border-blue-400"
      >
        <Pencil size={10} /> Asignar P
      </button>
    ) : (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-xs font-semibold cursor-pointer group",
          PROB_COLOR[scenario.probability] ?? "bg-gray-100 text-gray-600 border-gray-200",
        )}
        onClick={() => { setValue(scenario.probability!); setEditing(true); }}
        title="Clic para editar probabilidad"
      >
        P{scenario.probability} — {scenario.prob_level}
        <Pencil size={9} className="opacity-0 group-hover:opacity-60 transition-opacity" />
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1">
      <select
        value={value}
        onChange={e => setValue(Number(e.target.value))}
        className="text-xs border border-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
        autoFocus
      >
        {[1, 2, 3, 4, 5].map(v => (
          <option key={v} value={v}>{v} — {PROB_LEVEL[v]}</option>
        ))}
      </select>
      <button
        onClick={() => mut.mutate(value)}
        disabled={mut.isPending}
        className="p-0.5 text-green-600 hover:text-green-800 disabled:opacity-50"
        title="Guardar"
      >
        {mut.isPending ? <Loader size={12} className="animate-spin" /> : <Check size={12} />}
      </button>
      <button
        onClick={() => setEditing(false)}
        className="p-0.5 text-gray-400 hover:text-gray-600"
        title="Cancelar"
      >
        <X size={12} />
      </button>
    </span>
  );
}

// ─── ScenarioCard ─────────────────────────────────────────────────────────────

function ScenarioCard({
  scenario,
  onDelete,
  onUpdate,
}: {
  scenario: RiskScenarioOut;
  onDelete: () => void;
  onUpdate: () => void;
}) {
  const [open, setOpen] = useState(false);

  const { data: hallazgos, isLoading: loadingHallazgos } = useQuery({
    queryKey: ["scenario-hallazgos", scenario.id],
    queryFn: () => scenariosApi.getHallazgos(scenario.id).then(r => r.data),
    enabled: open,
  });

  // Use AI-generated title if available, fall back to consequence
  const displayTitle = scenario.title || scenario.consequence;
  const showConsequenceSubtitle =
    scenario.title && scenario.title !== scenario.consequence;

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4">
        {/* Collapse trigger (code + title only) */}
        <div
          onClick={() => setOpen(v => !v)}
          className="flex-1 flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity min-w-0"
        >
          <span className="text-xs font-bold text-indigo-600 w-14 flex-shrink-0">
            {scenario.scenario_code}
          </span>
          <span className="flex-1 text-sm font-medium text-gray-800 truncate">
            {displayTitle}
          </span>
          {scenario.asset_name && (
            <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-md font-medium border border-indigo-100 flex-shrink-0">
              {scenario.asset_name}
            </span>
          )}
        </div>

        {/* Right-side actions — NOT inside collapse trigger */}
        <div
          className="flex items-center gap-2 flex-shrink-0"
          onClick={e => e.stopPropagation()}
        >
          {STATUS_ICON[scenario.status]}
          <ProbabilityEditor scenario={scenario} onUpdated={onUpdate} />
          {scenario.finding_count != null && (
            <span className="text-xs text-gray-400 hidden sm:inline">
              {scenario.finding_count} hallazgos
            </span>
          )}
        </div>

        <button
          onClick={() => setOpen(v => !v)}
          className="p-1 text-gray-400 hover:text-gray-600 flex-shrink-0"
        >
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        <button
          onClick={e => { e.stopPropagation(); onDelete(); }}
          className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
          title="Eliminar escenario"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Expanded panel */}
      {open && (
        <div className="border-t border-gray-100 bg-gray-50 px-5 py-4 space-y-4">
          {/* Consequence subtitle when AI title differs */}
          {showConsequenceSubtitle && (
            <p className="text-xs text-gray-500">
              Agrupación técnica:{" "}
              <span className="font-mono text-gray-600">{scenario.consequence}</span>
            </p>
          )}

          {/* IA probability rationale */}
          {scenario.probability_rationale && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">
                Justificación IA — Probabilidad
              </p>
              <p className="text-sm text-blue-900 leading-relaxed">
                {scenario.probability_rationale}
              </p>
            </div>
          )}

          {/* Business process */}
          {scenario.business_process_name && (
            <p className="text-xs text-gray-500">
              Proceso vinculado:{" "}
              <span className="font-medium text-gray-700">{scenario.business_process_name}</span>
            </p>
          )}

          {/* Findings list */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <ShieldAlert size={13} className="text-gray-400" />
              <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                Hallazgos técnicos agrupados
              </p>
            </div>

            {loadingHallazgos ? (
              <div className="text-xs text-gray-400 py-4 text-center">
                <Loader size={13} className="animate-spin inline mr-1" /> Cargando hallazgos…
              </div>
            ) : hallazgos && hallazgos.length > 0 ? (
              <div className="space-y-2">
                {hallazgos.map(f => (
                  <FindingRow key={f.id} finding={f} />
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 italic py-2">Sin hallazgos vinculados.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── page ─────────────────────────────────────────────────────────────────────

export default function ProbabilidadPage() {
  const { project } = useProjectStore();
  const qc = useQueryClient();

  const { data: scenarios, isLoading } = useQuery({
    queryKey: ["scenarios", project?.id],
    queryFn: () => scenariosApi.list(project!.id).then(r => r.data),
    enabled: !!project,
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => scenariosApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenarios", project?.id] }),
  });

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Selecciona un proyecto para continuar.
      </div>
    );
  }

  const assessed = scenarios?.filter(s => s.probability != null).length ?? 0;
  const total = scenarios?.length ?? 0;
  const allAssessed = total > 0 && assessed === total;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Probabilidad</h1>
        <p className="text-sm text-gray-500 mt-1">
          Revisa y ajusta la probabilidad de materialización (1-5) de cada escenario.
          La IA ya asignó un valor recomendado en <strong>Escenarios</strong> — puedes editarlo haciendo clic en la etiqueta.
        </p>
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl px-5 py-4 flex items-center gap-4">
          <div className="flex-1">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Escenarios evaluados</span>
              <span className="font-medium">{assessed}/{total}</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${total > 0 ? (assessed / total) * 100 : 0}%` }}
              />
            </div>
          </div>
          {allAssessed && (
            <span className="text-xs text-green-600 font-medium flex items-center gap-1">
              <CheckCircle2 size={13} /> Completo
            </span>
          )}
        </div>
      )}

      {/* Hint when no scenarios */}
      {!isLoading && total === 0 && (
        <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
          <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
          <p>No hay escenarios generados todavía. Ve a <strong>Escenarios</strong> para consolidar los hallazgos con IA primero.</p>
        </div>
      )}

      {/* Scenario list */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : total === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <ShieldAlert size={36} className="mx-auto mb-3 opacity-40" />
          <p className="font-medium">No hay escenarios todavía</p>
          <p className="text-sm mt-1">
            Ve a <strong>Escenarios</strong> y usa el botón "Analizar con IA" para generar los escenarios.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {scenarios!.map(s => (
            <ScenarioCard
              key={s.id}
              scenario={s}
              onUpdate={() => qc.invalidateQueries({ queryKey: ["scenarios", project?.id] })}
              onDelete={() => {
                if (confirm(`¿Eliminar escenario ${s.scenario_code}? Esta acción no se puede deshacer.`)) {
                  deleteMut.mutate(s.id);
                }
              }}
            />
          ))}
        </div>
      )}

      {/* Next-step hint */}
      {allAssessed && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 flex items-center gap-3">
          <RefreshCw size={16} className="text-blue-500 flex-shrink-0" />
          <p className="text-sm text-blue-700">
            Todos los escenarios tienen probabilidad asignada. Continúa en{" "}
            <strong>Impacto</strong> para vincular cada escenario a un proceso de negocio.
          </p>
        </div>
      )}
    </div>
  );
}
