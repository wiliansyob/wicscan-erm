"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workspacesApi } from "@/lib/api";
import { Save, Loader, AlertCircle } from "lucide-react";

export const DEFAULT_RISK_CONFIG = {
  probabilities: {
    1: { name: "Muy Baja", description: "Es sumamente improbable que el evento ocurra." },
    2: { name: "Baja", description: "Es poco probable que el evento ocurra." },
    3: { name: "Media", description: "El evento podría ocurrir en algún momento." },
    4: { name: "Alta", description: "Es probable que el evento ocurra." },
    5: { name: "Muy Alta", description: "Es casi seguro que el evento ocurrirá." },
  },
  impacts: {
    1: { name: "Muy Bajo", description: "Impacto mínimo o imperceptible en el negocio." },
    2: { name: "Bajo", description: "Impacto menor que puede resolverse rápidamente." },
    3: { name: "Medio", description: "Impacto moderado, degradación temporal de servicios." },
    4: { name: "Alto", description: "Impacto severo, pérdida de datos o disrupción mayor." },
    5: { name: "Muy Alto", description: "Impacto catastrófico, paralización del negocio." },
  },
  levels: {
    low: { name: "Bajo", description: "Riesgo aceptable. Monitoreo rutinario." },
    medium: { name: "Medio", description: "Requiere atención a mediano plazo." },
    high: { name: "Alto", description: "Requiere mitigación a corto plazo." },
    critical: { name: "Crítico", description: "Requiere acción inmediata." },
  }
};

type Section = "all" | "pi" | "levels";

export function RiskCriteriaTab({ section = "all" }: { section?: Section }) {
  const qc = useQueryClient();
  const [toast, setToast] = useState<string | null>(null);

  const { data: settingsData, isLoading } = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: () => workspacesApi.getSettings().then((res) => res.data),
  });

  const [form, setForm] = useState(DEFAULT_RISK_CONFIG);

  useEffect(() => {
    if (settingsData?.ai_config?.risk_config) {
      setForm(settingsData.ai_config.risk_config);
    }
  }, [settingsData]);

  const mutation = useMutation({
    mutationFn: (newConfig: any) => {
      const mergedConfig = {
        ...settingsData?.ai_config,
        risk_config: newConfig,
      };
      return workspacesApi.updateSettings({ ai_config: mergedConfig });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspace-settings"] });
      setToast("Configuración guardada correctamente");
      setTimeout(() => setToast(null), 3000);
    },
  });

  const updateProp = (
    category: "probabilities" | "impacts" | "levels",
    key: string | number,
    field: "name" | "description",
    value: string
  ) => {
    setForm(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        // @ts-ignore
        [key]: { ...prev[category][key], [field]: value },
      },
    }));
  };

  if (isLoading) {
    return <div className="text-gray-400 text-sm py-12 text-center">Cargando configuración...</div>;
  }

  const showPI     = section === "all" || section === "pi";
  const showLevels = section === "all" || section === "levels";

  const headerTitle = section === "levels"
    ? "Niveles de Riesgo"
    : section === "pi"
    ? "Criterios de Probabilidad e Impacto"
    : "Criterios de Riesgo";

  const headerDesc = section === "levels"
    ? "Define las etiquetas y umbrales de los 4 niveles de riesgo de la matriz."
    : section === "pi"
    ? "Personaliza las escalas de probabilidad e impacto (1–5) para la evaluación de escenarios."
    : "Personaliza las definiciones para tu matriz de riesgos (5×5) y los 4 niveles de riesgo.";

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-8 space-y-8">
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 bg-gray-900 text-white text-sm px-4 py-3 rounded-xl shadow-lg">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">{headerTitle}</h2>
          <p className="text-sm text-gray-500 mt-1">{headerDesc}</p>
        </div>
        <button
          onClick={() => mutation.mutate(form)}
          disabled={mutation.isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
        >
          {mutation.isPending ? <Loader size={16} className="animate-spin" /> : <Save size={16} />}
          Guardar Cambios
        </button>
      </div>

      {showPI && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Probabilidad */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide flex items-center gap-2">
              <AlertCircle size={15} className="text-blue-500" /> Niveles de Probabilidad (Eje Y)
            </h3>
            <div className="space-y-3">
              {[5, 4, 3, 2, 1].map(n => (
                <div key={`p-${n}`} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="w-6 h-6 rounded bg-gray-200 text-gray-700 flex items-center justify-center text-xs font-bold">{n}</span>
                    <input
                      type="text"
                      value={form.probabilities[n as keyof typeof form.probabilities].name}
                      onChange={e => updateProp("probabilities", n, "name", e.target.value)}
                      className="flex-1 bg-white border border-gray-300 rounded px-2 py-1 text-sm font-semibold"
                      placeholder="Nombre (ej. Muy Alta)"
                    />
                  </div>
                  <textarea
                    value={form.probabilities[n as keyof typeof form.probabilities].description}
                    onChange={e => updateProp("probabilities", n, "description", e.target.value)}
                    className="w-full bg-white border border-gray-300 rounded px-2 py-1.5 text-xs text-gray-600 resize-none h-14"
                    placeholder="Descripción del nivel..."
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Impacto */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide flex items-center gap-2">
              <AlertCircle size={15} className="text-purple-500" /> Niveles de Impacto (Eje X)
            </h3>
            <div className="space-y-3">
              {[5, 4, 3, 2, 1].map(n => (
                <div key={`i-${n}`} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="w-6 h-6 rounded bg-gray-200 text-gray-700 flex items-center justify-center text-xs font-bold">{n}</span>
                    <input
                      type="text"
                      value={form.impacts[n as keyof typeof form.impacts].name}
                      onChange={e => updateProp("impacts", n, "name", e.target.value)}
                      className="flex-1 bg-white border border-gray-300 rounded px-2 py-1 text-sm font-semibold"
                      placeholder="Nombre (ej. Muy Alto)"
                    />
                  </div>
                  <textarea
                    value={form.impacts[n as keyof typeof form.impacts].description}
                    onChange={e => updateProp("impacts", n, "description", e.target.value)}
                    className="w-full bg-white border border-gray-300 rounded px-2 py-1.5 text-xs text-gray-600 resize-none h-14"
                    placeholder="Descripción del nivel..."
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {showLevels && (
        <div className={`space-y-4 ${showPI ? "pt-4 border-t" : ""}`}>
          <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide flex items-center gap-2">
            <AlertCircle size={15} className="text-red-500" /> Niveles de Riesgo
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { id: "critical", color: "bg-red-600" },
              { id: "high",     color: "bg-orange-500" },
              { id: "medium",   color: "bg-yellow-400" },
              { id: "low",      color: "bg-green-400" },
            ].map(level => (
              <div key={level.id} className="bg-white border border-gray-200 shadow-sm rounded-xl p-4 flex gap-3">
                <div className={`w-4 h-full rounded ${level.color}`} />
                <div className="flex-1 space-y-2">
                  <input
                    type="text"
                    // @ts-ignore
                    value={form.levels[level.id].name}
                    // @ts-ignore
                    onChange={e => updateProp("levels", level.id, "name", e.target.value)}
                    className="w-full bg-gray-50 border border-gray-300 rounded px-2 py-1 text-sm font-bold"
                  />
                  <textarea
                    // @ts-ignore
                    value={form.levels[level.id].description}
                    // @ts-ignore
                    onChange={e => updateProp("levels", level.id, "description", e.target.value)}
                    className="w-full bg-gray-50 border border-gray-300 rounded px-2 py-1.5 text-xs text-gray-600 resize-none h-12"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
