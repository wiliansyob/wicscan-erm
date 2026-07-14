"use client";

import { useState, useEffect } from "react";
import { useQuery, useQueries } from "@tanstack/react-query";
import { risksApi, findingsApi, scanSessionsApi, assetsApi, projectsApi, workspacesApi } from "@/lib/api";
import { useProjectStore } from "@/lib/project";
import {
  FileText, Download, Printer, ChevronDown, ChevronUp,
  CheckCircle, AlertTriangle, Shield, Target
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { RiskHeatmap } from "@/components/risks/risk-heatmap";
import { DEFAULT_RISK_CONFIG } from "@/components/risks/risk-criteria";

const LEVEL_COLOR: Record<string, string> = {
  critical: "bg-red-600",
  high: "bg-orange-500",
  medium: "bg-yellow-400",
  low: "bg-green-400",
};
const LEVEL_TEXT: Record<string, string> = {
  critical: "text-red-700", high: "text-orange-600", medium: "text-yellow-600", low: "text-green-700",
};
const LEVEL_BG: Record<string, string> = {
  critical: "bg-red-50 border-red-200", high: "bg-orange-50 border-orange-200",
  medium: "bg-yellow-50 border-yellow-200", low: "bg-green-50 border-green-200",
};
const TREATMENT_LABELS: Record<string, string> = {
  mitigate: "Reducir", avoid: "Evitar", transfer: "Transferir", accept: "Aceptar",
};
const STATUS_LABELS: Record<string, string> = {
  open: "Abierto", in_progress: "En proceso", mitigated: "Mitigado", accepted: "Aceptado",
};
const SCANNER_META: Record<string, { label: string; cls: string }> = {
  sonarqube: { label: "SAST",    cls: "bg-purple-100 text-purple-800" },
  zap:       { label: "DAST",    cls: "bg-emerald-100 text-emerald-800" },
  burp:      { label: "DAST",    cls: "bg-emerald-100 text-emerald-800" },
  manual:    { label: "Manual",  cls: "bg-gray-200 text-gray-700" },
  ethical:   { label: "Ethical", cls: "bg-teal-100 text-teal-800" },
  nessus:    { label: "VA",      cls: "bg-indigo-100 text-indigo-800" },
  openvas:   { label: "VA",      cls: "bg-indigo-100 text-indigo-800" },
};
function getScannerMeta(scanner?: string | null) {
  if (!scanner) return null;
  return SCANNER_META[scanner.toLowerCase()] ?? { label: scanner.toUpperCase(), cls: "bg-gray-200 text-gray-700" };
}
const IMPACT_LABELS: Record<string, string> = {
  impact_operational:  "Operacional",
  impact_financial:    "Financiero",
  impact_normative:    "Normativo",
  impact_reputational: "Reputacional",
};
const PRIORITY_LABELS_PDF: Record<string, string> = {
  immediate: "Inmediata", short_term: "Corto plazo", medium_term: "Mediano plazo", long_term: "Largo plazo",
};

export default function ReportePage() {
  const { project, assetId } = useProjectStore();
  const [expandedRisk, setExpandedRisk] = useState<string | null>(null);
  const [printing, setPrinting] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const { data: projectData } = useQuery({
    queryKey: ["project-detail", project?.id],
    queryFn: () => projectsApi.get(project!.id).then(r => r.data),
    enabled: !!project,
  });

  const { data: risksData, isLoading: loadingRisks } = useQuery({
    queryKey: ["risks-report", project?.id],
    queryFn: () => risksApi.list({ project_id: project?.id, size: 100 }).then(r => r.data),
    enabled: !!project,
  });

  const { data: findingsSummary } = useQuery({
    queryKey: ["findings-summary-report", project?.id],
    queryFn: () => findingsApi.summary({ project_id: project?.id }).then(r => r.data),
    enabled: !!project,
  });

  const { data: sessionsData } = useQuery({
    queryKey: ["sessions-report", project?.id],
    queryFn: () => scanSessionsApi.list(project!.id, { size: 5 }).then(r => r.data),
    enabled: !!project,
  });

  const { data: allFindingsData, isLoading: loadingFindings } = useQuery({
    queryKey: ["findings-report-all", project?.id],
    queryFn: () => findingsApi.list({ project_id: project?.id, size: 500 }).then(r => r.data),
    enabled: !!project,
  });

  const { data: settingsData } = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: () => workspacesApi.getSettings().then((res) => res.data),
  });

  const riskConfig = settingsData?.ai_config?.risk_config || DEFAULT_RISK_CONFIG;

  const PRIORITY_ORDER: Record<string, number> = { immediate: 4, short_term: 3, medium_term: 2, long_term: 1 };
  const PRIORITY_LABELS: Record<string, string> = { immediate: "Inmediata", short_term: "Corto plazo", medium_term: "Mediano plazo", long_term: "Largo plazo" };

  const risks: any[] = [...(risksData?.items ?? [])].sort((a, b) => {
    const pA = PRIORITY_ORDER[a.priority] || 0;
    const pB = PRIORITY_ORDER[b.priority] || 0;
    if (pA !== pB) return pB - pA;
    const scoreA = a.risk_score || (a.probability * a.impact) || 0;
    const scoreB = b.risk_score || (b.probability * b.impact) || 0;
    return scoreB - scoreA;
  });
  const sessions: any[] = sessionsData?.items ?? [];
  const allFindings: any[] = allFindingsData?.items ?? [];

  const allFindingIds = Array.from(new Set(risks.flatMap((r: any) => r.finding_ids || [])));

  const snippetQueries = useQueries({
    queries: allFindingIds.map((id: string) => ({
      queryKey: ["finding-snippet-report", id],
      queryFn: () => findingsApi.getSnippet(id).then(r => r.data),
      enabled: !!id,
    })),
  });

  const loadingSnippets = snippetQueries.some(q => q.isLoading);
  const snippetMap = Object.fromEntries(
    allFindingIds.map((id, index) => [id, snippetQueries[index].data?.content])
  );

  const countByLevel = (level: string) => risks.filter(r => r.risk_level === level).length;
  const countByStatus = (status: string) => risks.filter(r => r.status === status).length;

  const scannerBreakdown = allFindings.reduce((acc: Record<string, number>, f: any) => {
    const meta = getScannerMeta(f.scanner);
    const label = meta?.label ?? "Otro";
    acc[label] = (acc[label] || 0) + 1;
    return acc;
  }, {});

  const matrix = Array(5).fill(0).map(() => Array(5).fill(0));
  risks.forEach((r: any) => {
    const lIdx = r.probability ? r.probability - 1 : 0;
    const iIdx = r.impact ? r.impact - 1 : 0;
    r.likelihood_idx = lIdx;
    r.impact_idx = iIdx;
    
    if (matrix[4 - lIdx]) {
      matrix[4 - lIdx][iIdx] = (matrix[4 - lIdx][iIdx] || 0) + 1;
    }
  });

  const risksByLevel = ["critical", "high", "medium", "low"].map(l => ({
    level: l,
    count: countByLevel(l),
    risks: risks.filter(r => r.risk_level === l),
  })).filter(g => g.count > 0);

  const handlePrint = () => {
    setPrinting(true);
    setTimeout(() => { window.print(); setPrinting(false); }, 100);
  };

  useEffect(() => {
    if (showPreview) {
      document.body.style.overflow = "visible";
      document.documentElement.style.overflow = "visible";
    } else {
      document.body.style.overflow = "";
      document.documentElement.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
      document.documentElement.style.overflow = "";
    }
  }, [showPreview]);

  const handleExportPDF = async () => {
    try {
      // @ts-ignore
      const html2pdf = (await import("html2pdf.js")).default;
      const element = document.getElementById("pdf-export-content");
      if (!element) return;
      
      const opt = {
        margin:       [15, 15, 15, 15],
        filename:     `Reporte_Riesgos_${project?.name?.replace(/[^a-z0-9]/gi, '_')}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };

      html2pdf().set(opt).from(element).save();
    } catch (error) {
      console.error("Error al generar PDF:", error);
      alert("Hubo un error al generar el PDF.");
    }
  };

  const handleOpenPreviewWindow = () => {
    setShowPreview(true);
  };

  const today = format(new Date(), "d 'de' MMMM 'de' yyyy", { locale: es });

  if (loadingRisks || loadingFindings || loadingSnippets) {
    return <div className="text-gray-400 text-sm py-12 text-center">Generando reporte y recopilando evidencias...</div>;
  }

  return (
    <>
    <div className={cn("space-y-6", showPreview ? "hidden print:hidden" : "block")} id="report-content">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-blue-600 mb-1">{project?.name}</p>
          <h1 className="text-2xl font-bold text-gray-900">Reporte de Riesgo</h1>
          <p className="text-sm text-gray-500 mt-0.5">Generado el {today}</p>
        </div>
        <div className="flex gap-2 print:hidden no-export">
          <button onClick={handleOpenPreviewWindow}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl px-4 py-2.5 transition-colors">
            <FileText size={14} />
            Previsualizar y Exportar
          </button>
        </div>
      </div>

      {/* Executive summary */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-blue-600" />
          <h2 className="text-base font-semibold text-gray-900">Resumen Ejecutivo</h2>
        </div>

        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Total de riesgos", value: risks.length, icon: Shield, color: "text-blue-600" },
            { label: "Hallazgos escaneados", value: findingsSummary?.total ?? "—", icon: Target, color: "text-purple-600" },
            { label: "Riesgos con tratamiento", value: risks.filter(r => (r.treatments?.length ?? 0) > 0).length, icon: CheckCircle, color: "text-green-600" },
            { label: "Sesiones de escaneo", value: sessions.length, icon: AlertTriangle, color: "text-orange-600" },
          ].map(card => (
            <div key={card.label} className="bg-gray-50 rounded-xl p-4 text-center">
              <card.icon size={20} className={cn("mx-auto mb-2", card.color)} />
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{card.label}</p>
            </div>
          ))}
        </div>

        {/* Risk level distribution */}
        <div>
          <p className="text-xs font-medium text-gray-500 mb-3 uppercase tracking-wide">Distribución por nivel de riesgo</p>
          <div className="grid grid-cols-4 gap-3">
            {["critical", "high", "medium", "low"].map(level => (
              <div key={level} className={cn("rounded-lg border px-4 py-3", LEVEL_BG[level] ?? "bg-gray-50 border-gray-200")}>
                <p className={cn("text-xl font-bold", LEVEL_TEXT[level] ?? "text-gray-700")}>{countByLevel(level)}</p>
                <p className={cn("text-xs capitalize font-medium", LEVEL_TEXT[level] ?? "text-gray-500")}>{level}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Status distribution */}
        {risks.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 mb-3 uppercase tracking-wide">Estado de los riesgos</p>
            <div className="flex items-center gap-2">
              {Object.entries(STATUS_LABELS).map(([status, label]) => {
                const count = countByStatus(status);
                if (!count) return null;
                return (
                  <div key={status} className="flex items-center gap-1.5 bg-gray-100 rounded-full px-3 py-1.5">
                    <span className="text-xs font-semibold text-gray-800">{count}</span>
                    <span className="text-xs text-gray-500">{label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {risks.length === 0 && (
        <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-12 text-center">
          <FileText size={32} className="mx-auto mb-3 text-gray-200" />
          <p className="text-gray-400 text-sm">No hay riesgos registrados para este proyecto.</p>
          <p className="text-gray-300 text-xs mt-1">Completa las fases de Identificación y Análisis primero.</p>
        </div>
      )}

      {/* Footer */}
      {risks.length > 0 && (
        <div className="border-t border-gray-100 pt-4 text-center text-xs text-gray-300">
          WicScan Risk Manager · Generado el {today} · ISO 31000
        </div>
      )}

    </div>

      {/* Hidden printable A4 layout or Inline Preview */}
      <style>{`
        @media print {
          @page { margin: 8mm; size: A4 portrait; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; background-color: white !important; }
          .no-export { display: none !important; }
          .page-break { page-break-after: always; }
        }
      `}</style>
      {showPreview && (
        <div className="fixed top-6 right-6 flex gap-3 z-[200] no-export">
          <button onClick={() => setShowPreview(false)} className="px-4 py-2 bg-white text-gray-700 font-medium rounded-lg shadow-xl hover:bg-gray-50 border border-gray-200 transition-colors">
            Cerrar Previsualización
          </button>
          <button onClick={() => window.print()} className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg shadow-xl hover:bg-blue-700 transition-colors flex items-center gap-2">
            <Printer size={16} /> Imprimir / PDF
          </button>
        </div>
      )}
      <div 
        id="pdf-export-content" 
        className={cn(
          "text-black text-xs font-sans",
          showPreview 
            ? "absolute top-0 left-0 w-full z-[100] min-h-screen bg-gray-500/80 backdrop-blur-sm print:bg-white print:backdrop-blur-none flex justify-center py-10 print:py-0 print:block" 
            : "absolute top-[-10000px] left-[-10000px] w-[800px] print:hidden"
        )}
      >
        <div className={cn("bg-white", showPreview ? "relative z-50 mb-20 shadow-xl print:shadow-none min-h-[1130px] w-[800px] print:w-full print:mx-auto" : "w-[800px]")}>
          {/* Header Reporte PDF */}
        <div className="h-[800px] relative flex flex-col justify-center items-center text-center p-12 bg-white" style={{ pageBreakAfter: 'always' }}>
          
          <div className="relative z-10 space-y-5 w-full px-12">
            <div className="w-20 h-20 bg-blue-900 rounded-full mx-auto flex items-center justify-center mb-6">
              <Shield size={40} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold text-gray-900 uppercase tracking-wide">Informe de gestión de riesgos</h1>
            <div className="h-[2px] w-16 bg-blue-600 mx-auto rounded"></div>
            <h2 className="text-2xl font-medium text-gray-700 pt-3">App: {project?.name || 'General'}</h2>
          </div>
          
          <div className="absolute bottom-32 right-16 text-right">
            <p className="text-lg font-semibold text-gray-900">{today}</p>
            <p className="text-base text-gray-500 mt-1">Revisión 1.0</p>
          </div>
        </div>

        {/* 1. Introducción */}
        <div className="p-10 space-y-6" style={{ pageBreakAfter: 'always' }}>
          <h2 className="text-xl font-bold text-blue-900 uppercase border-b-2 border-blue-900 pb-2">1. Introducción</h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-blue-700">1.1 Objetivo</h3>
              <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap leading-relaxed">
                {settingsData?.ai_config?.report_config?.objective || "El objetivo principal de este análisis es identificar, evaluar y clasificar los riesgos de seguridad descubiertos."}
              </p>
            </div>
            
            <div className="pt-4">
              <h3 className="text-lg font-semibold text-blue-700">1.2 Alcance</h3>
              <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap leading-relaxed">
                {settingsData?.ai_config?.report_config?.scope || "El alcance comprende la infraestructura técnica, aplicaciones web expuestas y componentes relevantes."}
              </p>
            </div>
          </div>
        </div>

        {/* 2. Criterios para la gestión de riesgos */}
        <div className="p-10 space-y-6" style={{ pageBreakAfter: 'always' }}>
          <h2 className="text-xl font-bold text-blue-900 uppercase border-b-2 border-blue-900 pb-2">2. Criterios para la gestión de riesgos</h2>
          <p className="text-sm text-gray-700 mb-6">El siguiente marco de referencia define cómo se evaluó la probabilidad y el impacto de los riesgos hallados en la plataforma.</p>
          
          <h3 className="text-lg font-semibold text-blue-700">2.1 Probabilidad</h3>
          <table className="w-full text-sm border-collapse border border-gray-300 mb-8">
            <thead className="bg-gray-100 text-gray-900">
              <tr>
                <th className="border border-gray-300 px-4 py-2 text-center font-bold w-16">Nivel</th>
                <th className="border border-gray-300 px-4 py-2 text-left font-bold w-1/4">Nombre</th>
                <th className="border border-gray-300 px-4 py-2 text-left font-bold">Descripción</th>
              </tr>
            </thead>
            <tbody>
              {[5,4,3,2,1].map(n => (
                <tr key={n}>
                  <td className="border border-gray-300 px-4 py-2 text-center font-bold text-gray-700">{n}</td>
                  <td className="border border-gray-300 px-4 py-2 text-gray-900 font-medium">{riskConfig.probabilities[n]?.name || n}</td>
                  <td className="border border-gray-300 px-4 py-2 text-gray-700">{riskConfig.probabilities[n]?.description}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3 className="text-lg font-semibold text-blue-700">2.2 Impacto</h3>
          <table className="w-full text-sm border-collapse border border-gray-300 mb-8">
            <thead className="bg-gray-100 text-gray-900">
              <tr>
                <th className="border border-gray-300 px-4 py-2 text-center font-bold w-16">Nivel</th>
                <th className="border border-gray-300 px-4 py-2 text-left font-bold w-1/4">Nombre</th>
                <th className="border border-gray-300 px-4 py-2 text-left font-bold">Descripción</th>
              </tr>
            </thead>
            <tbody>
              {[5,4,3,2,1].map(n => (
                <tr key={n}>
                  <td className="border border-gray-300 px-4 py-2 text-center font-bold text-gray-700">{n}</td>
                  <td className="border border-gray-300 px-4 py-2 text-gray-900 font-medium">{riskConfig.impacts[n]?.name || n}</td>
                  <td className="border border-gray-300 px-4 py-2 text-gray-700">{riskConfig.impacts[n]?.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 3. Clasificación de Riesgo */}
        {risks.length > 0 && (
          <div className="p-10 space-y-6" style={{ pageBreakAfter: 'always' }}>
            <h2 className="text-xl font-bold text-blue-900 uppercase border-b-2 border-blue-900 pb-2">3. Clasificación de Riesgo</h2>
            <p className="text-sm text-gray-700 mb-6">Este capítulo detalla la matriz resultante combinando los niveles de probabilidad e impacto para determinar el nivel de riesgo final y las acciones requeridas.</p>

            <h3 className="text-lg font-semibold text-blue-700">3.1 Niveles de riesgo</h3>
            <table className="w-full text-sm border-collapse border border-gray-300 mb-8">
              <thead className="bg-gray-100 text-gray-900">
                <tr>
                  <th className="border border-gray-300 px-4 py-2 text-left font-bold w-1/4">Nivel de Riesgo</th>
                  <th className="border border-gray-300 px-4 py-2 text-left font-bold">Descripción / Acción Requerida</th>
                </tr>
              </thead>
              <tbody>
                {["critical", "high", "medium", "low"].map(key => (
                  <tr key={key}>
                    <td className={cn("border border-gray-300 px-4 py-2 font-bold uppercase", LEVEL_TEXT[key])}>
                      {riskConfig.levels[key]?.name || key}
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-gray-700">
                      {riskConfig.levels[key]?.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h3 className="text-lg font-semibold text-blue-700 mb-6">3.2 Mapa de Calor</h3>
            <div className="bg-white border border-gray-200 rounded-xl p-8 max-w-[600px] mx-auto shadow-sm">
              <RiskHeatmap matrix={matrix} risks={risks} riskConfig={riskConfig} />
            </div>
          </div>
        )}

        {/* 4. Resumen Ejecutivo */}
        <div className="p-10 space-y-6" style={{ pageBreakAfter: 'always' }}>
          <h2 className="text-xl font-bold text-blue-900 uppercase border-b-2 border-blue-900 pb-2">4. Resumen Ejecutivo</h2>
          <p className="text-sm text-gray-700 mb-4">A continuación, se presenta una visión general de la postura de riesgo actual, mostrando métricas clave y la distribución de los hallazgos por nivel de criticidad.</p>

          <div className="grid grid-cols-2 gap-4 mb-8">
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
              <Shield size={24} className="mx-auto mb-2 text-blue-600" />
              <p className="text-3xl font-bold text-gray-900">{risks.length}</p>
              <p className="text-sm font-medium text-gray-600">Total de riesgos evaluados</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
              <Target size={24} className="mx-auto mb-2 text-purple-600" />
              <p className="text-3xl font-bold text-gray-900">{findingsSummary?.total ?? 0}</p>
              <p className="text-sm font-medium text-gray-600">Hallazgos técnicos subyacentes</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
              <CheckCircle size={24} className="mx-auto mb-2 text-green-600" />
              <p className="text-3xl font-bold text-gray-900">{risks.filter(r => (r.treatments?.length ?? 0) > 0).length}</p>
              <p className="text-sm font-medium text-gray-600">Riesgos con plan de tratamiento</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
              <AlertTriangle size={24} className="mx-auto mb-2 text-orange-600" />
              <p className="text-3xl font-bold text-gray-900">{sessions.length}</p>
              <p className="text-sm font-medium text-gray-600">Sesiones de escaneo consolidadas</p>
            </div>
          </div>

          <h3 className="text-lg font-semibold text-blue-700 mb-4">Distribución por Nivel</h3>
          <div className="grid grid-cols-4 gap-3 mb-8">
            {["critical", "high", "medium", "low"].map(level => (
              <div key={level} className={cn("rounded-lg border px-4 py-3 text-center", LEVEL_BG[level] ?? "bg-gray-50 border-gray-200")}>
                <p className={cn("text-2xl font-bold", LEVEL_TEXT[level] ?? "text-gray-700")}>{countByLevel(level)}</p>
                <p className={cn("text-sm font-medium uppercase mt-1", LEVEL_TEXT[level] ?? "text-gray-500")}>
                  {riskConfig.levels[level]?.name || level}
                </p>
              </div>
            ))}
          </div>

          {Object.keys(scannerBreakdown).length > 0 && (
            <>
              <h3 className="text-lg font-semibold text-blue-700 mb-4 mt-8">Fuentes de análisis</h3>
              <div className="flex gap-3 flex-wrap mb-6">
                {Object.entries(scannerBreakdown).map(([label, count]) => (
                  <div key={label} className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 text-center">
                    <p className="text-lg font-bold text-gray-900">{count}</p>
                    <p className="text-xs font-medium text-gray-500">{label}</p>
                  </div>
                ))}
              </div>
            </>
          )}

          <h3 className="text-lg font-semibold text-blue-700 mb-4 mt-8">Tabla de Resumen</h3>
          <table className="w-full text-sm border-collapse border border-gray-300">
            <thead className="bg-gray-100 text-gray-900">
              <tr>
                <th className="border border-gray-300 px-4 py-2 text-left font-bold">Código</th>
                <th className="border border-gray-300 px-4 py-2 text-left font-bold">Título de la incidencia</th>
                <th className="border border-gray-300 px-4 py-2 text-center font-bold">P×I</th>
                <th className="border border-gray-300 px-4 py-2 text-center font-bold">Nivel</th>
                <th className="border border-gray-300 px-4 py-2 text-center font-bold">Tratamiento</th>
                <th className="border border-gray-300 px-4 py-2 text-center font-bold">Estado</th>
              </tr>
            </thead>
            <tbody>
              {risks.map(r => (
                <tr key={r.id}>
                  <td className="border border-gray-300 px-4 py-2 text-gray-900 font-medium whitespace-nowrap">{r.risk_code || "R-?"}</td>
                  <td className="border border-gray-300 px-4 py-2 text-gray-900">{r.risk_title}</td>
                  <td className="border border-gray-300 px-4 py-2 text-center text-gray-700">{r.probability}×{r.impact}={r.risk_score ?? r.probability * r.impact}</td>
                  <td className={cn("border border-gray-300 px-4 py-2 text-center font-bold uppercase", LEVEL_TEXT[r.risk_level])}>
                    {riskConfig.levels[r.risk_level]?.name || r.risk_level}
                  </td>
                  <td className="border border-gray-300 px-4 py-2 text-center text-gray-700">
                    {(r.treatments?.length ?? 0) > 0 ? `${r.treatments.length} acción${r.treatments.length !== 1 ? "es" : ""}` : "—"}
                  </td>
                  <td className="border border-gray-300 px-4 py-2 text-center text-gray-800">
                    {STATUS_LABELS[r.status] ?? r.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 5. Análisis */}
        {risks.length > 0 && (
          <div className="p-10 space-y-6">
            <h2 className="text-xl font-bold text-blue-900 uppercase border-b-2 border-blue-900 pb-2">5. Análisis</h2>
            <p className="text-sm text-gray-700 mb-6">Este capítulo detalla de forma individualizada cada uno de los riesgos evaluados, incluyendo su impacto en el negocio, evidencias técnicas y planes de tratamiento propuestos.</p>

            <h3 className="text-lg font-semibold text-blue-700">5.1 Hallazgos</h3>
            
            <div className="space-y-6 mt-6">
              {risks.map((r, idx) => (
                <div key={`detail-${r.id}`} className="mb-6" style={{ pageBreakBefore: idx === 0 ? 'auto' : 'always' }}>
                  <table className="w-full text-xs border-collapse border border-blue-300 mb-4">
                    <tbody>
                      <tr>
                        <td className="border border-blue-300 bg-blue-50 px-3 py-1.5 font-bold text-blue-900 w-1/4">RIESGO</td>
                        <td colSpan={3} className="border border-blue-300 px-3 py-1.5 font-semibold text-gray-900">{r.risk_title}</td>
                      </tr>
                      <tr>
                        <td className="border border-blue-300 bg-blue-50 px-3 py-1.5 font-bold text-blue-900">Código ID</td>
                        <td className="border border-blue-300 px-3 py-1.5 text-gray-900 w-1/4">{r.risk_code || "R-?"}</td>
                        <td className="border border-blue-300 bg-blue-50 px-3 py-1.5 font-bold text-blue-900 w-1/4">Nivel</td>
                        <td className={cn("border border-blue-300 px-3 py-1.5 font-bold uppercase", LEVEL_TEXT[r.risk_level])}>
                          {riskConfig.levels[r.risk_level]?.name || r.risk_level}
                        </td>
                      </tr>
                      <tr>
                        <td className="border border-blue-300 bg-blue-50 px-3 py-1.5 font-bold text-blue-900">Proyecto</td>
                        <td className="border border-blue-300 px-3 py-1.5 text-gray-900">
                          {project?.name || "General"}
                        </td>
                        <td className="border border-blue-300 bg-blue-50 px-3 py-1.5 font-bold text-blue-900 w-1/4">Prioridad</td>
                        <td className="border border-blue-300 px-3 py-1.5 text-gray-900 font-bold uppercase">
                          {PRIORITY_LABELS_PDF[r.priority] || PRIORITY_LABELS[r.priority] || "Mediano plazo"}
                        </td>
                      </tr>
                      <tr>
                        <td className="border border-blue-300 bg-blue-50 px-3 py-1.5 font-bold text-blue-900">Probabilidad</td>
                        <td className="border border-blue-300 px-3 py-1.5 text-gray-900">
                          {r.probability ?? "—"}{r.prob_level ? ` — ${r.prob_level}` : ""}
                        </td>
                        <td className="border border-blue-300 bg-blue-50 px-3 py-1.5 font-bold text-blue-900">Impacto</td>
                        <td className="border border-blue-300 px-3 py-1.5 text-gray-900">
                          {r.impact ?? "—"}{r.impact_level ? ` — ${r.impact_level}` : ""}
                        </td>
                      </tr>
                      {(r.impact_operational || r.impact_financial || r.impact_normative || r.impact_reputational) && (
                        <tr>
                          <td colSpan={4} className="border border-blue-300 px-3 py-2 bg-white">
                            <div className="grid grid-cols-4 gap-2">
                              {["impact_operational","impact_financial","impact_normative","impact_reputational"].map(key => (
                                r[key] ? (
                                  <div key={key} className="text-center">
                                    <p className="text-[9px] text-gray-500 uppercase font-semibold">{IMPACT_LABELS[key]}</p>
                                    <p className="text-xs font-bold text-gray-800">{r[key]}</p>
                                  </div>
                                ) : null
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                      <tr>
                        <td colSpan={4} className="border border-blue-300 bg-gray-100 px-3 py-1.5 font-bold text-gray-900">
                          Descripción y Evaluación
                        </td>
                      </tr>
                      <tr>
                        <td colSpan={4} className="border border-blue-300 px-3 py-2.5 text-gray-800 leading-relaxed text-xs">
                          <p className="whitespace-pre-wrap">{r.risk_description || "Sin descripción detallada."}</p>
                          {r.business_impact_desc && (
                            <p className="mt-2 text-gray-600 whitespace-pre-wrap"><strong>Impacto de negocio:</strong> {r.business_impact_desc}</p>
                          )}
                          {r.likelihood_rationale && (
                            <p className="mt-1 text-gray-600"><strong>Justificación probabilidad:</strong> {r.likelihood_rationale}</p>
                          )}
                          {r.impact_rationale && (
                            <p className="mt-1 text-gray-600"><strong>Justificación impacto:</strong> {r.impact_rationale}</p>
                          )}
                        </td>
                      </tr>
                      {r.treatments && r.treatments.length > 0 && (
                        <>
                          <tr>
                            <td colSpan={4} className="border border-blue-300 bg-gray-100 px-3 py-1.5 font-bold text-gray-900">
                              Plan de Tratamiento ({r.treatments.length} acción{r.treatments.length !== 1 ? "es" : ""})
                            </td>
                          </tr>
                          <tr>
                            <td colSpan={4} className="border border-blue-300 px-3 py-2 bg-white">
                              <div className="space-y-2">
                                {r.treatments.map((t: any, ti: number) => (
                                  <div key={t.id} className="border border-gray-200 rounded p-2 bg-gray-50">
                                    <div className="flex items-start gap-2">
                                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 uppercase flex-shrink-0 mt-0.5">
                                        {TREATMENT_LABELS[t.treatment_type] || t.treatment_type}
                                      </span>
                                      <div className="flex-1 min-w-0">
                                        <p className="text-xs font-semibold text-gray-900">{ti + 1}. {t.title}</p>
                                        {t.description && <p className="text-[10px] text-gray-600 mt-0.5">{t.description}</p>}
                                        <div className="flex items-center gap-3 mt-1 text-[9px] text-gray-500">
                                          {t.owner_name && <span>Responsable: <strong>{t.owner_name}</strong></span>}
                                          {t.due_date && <span>Fecha: <strong>{format(new Date(t.due_date), "d MMM yyyy", { locale: es })}</strong></span>}
                                          {t.priority && <span>Prioridad: <strong>{PRIORITY_LABELS_PDF[t.priority] || t.priority}</strong></span>}
                                          {t.expected_risk_reduction && <span>Reducción: <strong>{t.expected_risk_reduction}%</strong></span>}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </td>
                          </tr>
                        </>
                      )}
                      {(!r.treatments || r.treatments.length === 0) && (
                        <tr>
                          <td colSpan={4} className="border border-blue-300 px-3 py-2 text-[10px] text-gray-400 italic bg-white">
                            Sin acciones de tratamiento registradas.
                          </td>
                        </tr>
                      )}
                      {(() => {
                        const riskFindings = allFindings.filter((f: any) => r.finding_ids?.includes(f.id));
                        if (riskFindings.length === 0) return null;
                        return (
                          <>
                            <tr>
                              <td colSpan={4} className="border border-blue-300 bg-gray-100 px-3 py-1.5 font-bold text-gray-900">
                                Evidencias Vinculadas ({riskFindings.length})
                              </td>
                            </tr>
                            <tr>
                              <td colSpan={4} className="border border-blue-300 px-3 py-2.5 bg-white">
                                <div className="space-y-3">
                                  {riskFindings.map((f: any) => {
                                    const sm = getScannerMeta(f.scanner);
                                    return (
                                      <div key={f.id} className="bg-gray-50 border border-gray-300 rounded-lg p-2.5" style={{ pageBreakInside: 'avoid' }}>
                                        {/* Header: título + badges */}
                                        <p className="font-semibold text-gray-800 text-xs mb-1.5">{f.title}</p>
                                        <div className="flex items-center gap-1.5 mb-2 text-[10px] flex-wrap">
                                          {f.scanner && (
                                            <span className="bg-blue-100 px-1.5 py-0.5 rounded font-medium text-blue-800 uppercase">{f.scanner}</span>
                                          )}
                                          {sm && (
                                            <span className={cn("px-1.5 py-0.5 rounded font-bold uppercase", sm.cls)}>{sm.label}</span>
                                          )}
                                          {f.severity && (
                                            <span className={cn("px-1.5 py-0.5 rounded font-bold uppercase",
                                              f.severity === "critical" ? "bg-red-100 text-red-800" :
                                              f.severity === "high"     ? "bg-orange-100 text-orange-800" :
                                              f.severity === "medium"   ? "bg-yellow-100 text-yellow-800" :
                                              f.severity === "low"      ? "bg-blue-100 text-blue-800" :
                                              "bg-gray-200 text-gray-700"
                                            )}>{f.severity}</span>
                                          )}
                                          {f.cvss_score && <span className="bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded font-mono">CVSS {f.cvss_score}</span>}
                                          {f.cwe && <span className="font-mono text-gray-500">CWE-{f.cwe}</span>}
                                          {f.owasp_category && <span className="font-mono text-gray-500">{f.owasp_category}</span>}
                                        </div>

                                        {/* URL / archivo */}
                                        {f.file_path && (
                                          <p className="text-[10px] font-mono text-gray-500 bg-gray-200 px-2 py-0.5 rounded mb-2 break-all">
                                            {f.file_path}{f.line_start ? `:${f.line_start}` : ""}
                                          </p>
                                        )}

                                        {/* Descripción */}
                                        {f.description && (
                                          <div className="mb-2">
                                            <p className="text-[9px] font-bold text-gray-600 uppercase tracking-wide mb-0.5">Descripción</p>
                                            <p className="text-[10px] text-gray-700 leading-relaxed">{f.description}</p>
                                          </div>
                                        )}

                                        {/* Remediación */}
                                        {f.remediation_guidance && (
                                          <div className="mb-2 bg-green-50 border border-green-200 rounded p-1.5">
                                            <p className="text-[9px] font-bold text-green-700 uppercase tracking-wide mb-0.5">Remediación</p>
                                            <p className="text-[10px] text-green-800 leading-relaxed">{f.remediation_guidance}</p>
                                          </div>
                                        )}

                                        {/* Snippet de código (solo SAST) */}
                                        {snippetMap[f.id] && (
                                          <div>
                                            <p className="text-[9px] font-bold text-gray-600 uppercase tracking-wide mb-0.5">Fragmento de código</p>
                                            <pre className="text-[9px] bg-gray-900 text-gray-100 p-2 rounded-md overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed border border-gray-700">
                                              <code>{snippetMap[f.id]}</code>
                                            </pre>
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              </td>
                            </tr>
                          </>
                        );
                      })()}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
    </>
  );
}
