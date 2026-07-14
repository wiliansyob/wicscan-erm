"use client";

import { cn } from "@/lib/utils";

interface RiskHeatmapProps {
  matrix?: number[][];
  risks: Array<any>;
  riskConfig?: any;
  onRiskClick?: (riskId: string) => void;
}

function cellColor(p: number, i: number): string {
  const score = p * i;
  if (score >= 20) return "bg-red-500";
  if (score >= 12) return "bg-orange-400";
  if (score >= 6)  return "bg-yellow-300";
  return "bg-[#2FCC4C]";
}

export function RiskHeatmap({ risks, riskConfig, onRiskClick }: RiskHeatmapProps) {
  // Configs fallback just in case
  const defaultRiskConfig = {
    levels: {
      critical: { name: "Crítico" },
      high: { name: "Alto" },
      medium: { name: "Medio" },
      low: { name: "Bajo" }
    },
    probabilities: {
      5: { name: "Muy alta" }, 4: { name: "Alta" }, 3: { name: "Media" }, 2: { name: "Baja" }, 1: { name: "Muy baja" }
    },
    impacts: {
      1: { name: "Mínimo" }, 2: { name: "Menor" }, 3: { name: "Moderado" }, 4: { name: "Mayor" }, 5: { name: "Crítico" }
    }
  };
  const config = riskConfig || defaultRiskConfig;

  return (
    <div className="w-full">
      {/* Cabecera: título + leyenda */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <h2 className="text-sm font-semibold text-gray-700">Matriz de Riesgo ISO 31000</h2>
        <div className="flex flex-wrap items-center gap-3 md:gap-5">
          {[
            { label: `${config.levels.critical.name} ≥ 20`, color: "bg-red-500" },
            { label: `${config.levels.high.name} ≥ 12`,    color: "bg-orange-400" },
            { label: `${config.levels.medium.name} ≥ 6`,    color: "bg-yellow-300" },
            { label: `${config.levels.low.name} < 6`,     color: "bg-[#2FCC4C]" },
          ].map(l => (
            <div key={l.label} className="flex items-center gap-2">
              <div className={cn("w-3 h-3 rounded flex-shrink-0", l.color)} />
              <span className="text-xs text-gray-500 whitespace-nowrap">{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Cuerpo: eje Y izquierdo + matriz */}
      <div className="flex items-stretch gap-2">

        {/* Label "Probabilidad" rotado + números */}
        <div className="flex gap-2 flex-shrink-0">
          {/* Label vertical */}
          <div className="flex items-center justify-center w-5">
            <span
              className="text-xs text-gray-400 font-medium tracking-widest whitespace-nowrap"
              style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
            >
              Probabilidad →
            </span>
          </div>
          {/* Números Y */}
          <div className="flex flex-col justify-around pb-9">
            {[5,4,3,2,1].map(p => (
              <div key={p} className="flex flex-col items-end w-16 md:w-20">
                <span className="text-[10px] md:text-xs font-semibold text-gray-400 text-right">
                  {p} - {config.probabilities[p]?.name || p}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Matriz + eje X */}
        <div className="flex-1 min-w-0">
          {/* Filas de la matriz */}
          <div className="space-y-1.5">
            {[5,4,3,2,1].map(p => (
              <div key={p} className="flex gap-1.5">
                {[1,2,3,4,5].map(i => {
                  const risksHere = risks.filter((r: any) =>
                    (r.probability === p && r.impact === i) || 
                    (r.likelihood_idx === p - 1 && r.impact_idx === i - 1)
                  );
                  return (
                    <div
                      key={i}
                      className={cn(
                        "flex-1 min-h-[50px] md:min-h-[80px] rounded-lg flex flex-col items-center justify-center gap-1.5 p-1 md:p-2 relative group transition-all",
                        cellColor(p, i),
                        (risksHere.length > 0 && onRiskClick) ? "cursor-pointer hover:brightness-95 hover:shadow-lg" : "cursor-default"
                      )}
                    >
                      {risksHere.length > 0 && (
                        <div className="flex justify-center items-center w-full h-full">
                          <span className="bg-white/95 text-gray-900 text-sm md:text-base font-bold min-w-[32px] h-[32px] px-2 flex items-center justify-center rounded-full shadow-md">
                            {risksHere.length}
                          </span>
                        </div>
                      )}

                      {/* Tooltip */}
                      {risksHere.length > 0 && (
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-20 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                          <div className="bg-gray-900 text-white rounded-xl shadow-xl px-4 py-3 w-64 space-y-2">
                            {risksHere.map((r: any) => (
                              <div key={r.id}>
                                <p className="text-xs font-bold text-gray-100 font-mono">{r.risk_code}</p>
                                <p className="text-xs text-gray-300 leading-snug mt-0.5">{r.risk_title}</p>
                                <p className="text-xs text-gray-500 mt-1">
                                  P:{r.probability} × I:{r.impact} = <span className="font-semibold text-gray-300">{r.risk_score || (r.probability * r.impact)}</span>
                                  {r.finding_ids?.length > 0 && ` · ${r.finding_ids.length} evidencias`}
                                </p>
                              </div>
                            ))}
                          </div>
                          <div className="w-3 h-3 bg-gray-900 rotate-45 mx-auto -mt-1.5" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Labels X: Impacto */}
          <div className="flex mt-3 pl-1.5">
            {[1,2,3,4,5].map(i => (
              <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                <span className="text-xs font-semibold text-gray-400">{i}</span>
                <span className="text-[9px] md:text-[10px] text-gray-400 truncate max-w-[50px] md:max-w-[80px] text-center" title={config.impacts[i]?.name || String(i)}>
                  {config.impacts[i]?.name || i}
                </span>
              </div>
            ))}
          </div>
          <div className="text-center mt-3">
            <span className="text-xs text-gray-400 font-medium tracking-widest">Impacto →</span>
          </div>
        </div>
      </div>
    </div>
  );
}
