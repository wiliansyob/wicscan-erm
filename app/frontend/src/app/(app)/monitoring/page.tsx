"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { scanSessionsApi, risksApi, workspacesApi } from "@/lib/api";
import { useProjectStore } from "@/lib/project";
import { CheckCircle, XCircle, Clock, Activity, Server, ShieldAlert, Cpu, Database } from "lucide-react";
import { ScannersManager } from "./scanners-manager";

interface ServiceStatus {
  name: string;
  url: string;
  icon: React.ReactNode;
  status: "ok" | "error" | "checking";
  latency?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function checkService(url: string): Promise<{ ok: boolean; latency: number }> {
  const t0 = performance.now();
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(5000), cache: "no-store" });
    if (url.startsWith("/api/health/")) {
      // Proxy routes return JSON { ok, latency }
      const data = await res.json();
      return { ok: data.ok, latency: data.latency ?? Math.round(performance.now() - t0) };
    }
    return { ok: res.ok, latency: Math.round(performance.now() - t0) };
  } catch {
    return { ok: false, latency: Math.round(performance.now() - t0) };
  }
}

export default function MonitoringPage() {
  const { project, assetId } = useProjectStore();
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "Backend API", url: `${API_BASE}/health`, icon: <Server size={16} />, status: "checking" },
    { name: "Scanner Manager", url: "/api/health/scanner", icon: <Cpu size={16} />, status: "checking" },
    { name: "AI Gateway", url: "/api/health/ai", icon: <Cpu size={16} />, status: "checking" },
  ]);

  const [dbStatus, setDbStatus] = useState<{postgres: string, redis: string}>({postgres: "checking", redis: "checking"});

  const [aiProviders, setAiProviders] = useState<Record<string, boolean | "checking">>({});

  useEffect(() => {
    const check = async () => {
      const results = await Promise.all(
        services.map(async (s) => {
          const t0 = performance.now();
          try {
            const res = await fetch(s.url, { signal: AbortSignal.timeout(5000), cache: "no-store" });
            const data = await res.json().catch(() => null);
            
            // Si es el Backend API, parseamos los status de DB y Redis
            if (s.name === "Backend API" && data) {
              setDbStatus({
                postgres: data.postgres || "error",
                redis: data.redis_celery || "error"
              });
            }
            
            if (s.url.startsWith("/api/health/")) {
              return { ok: data?.ok, latency: data?.latency ?? Math.round(performance.now() - t0) };
            }
            return { ok: res.ok, latency: Math.round(performance.now() - t0) };
          } catch {
            if (s.name === "Backend API") setDbStatus({ postgres: "error", redis: "error" });
            return { ok: false, latency: Math.round(performance.now() - t0) };
          }
        })
      );
      
      setServices((prev) =>
        prev.map((s, i) => ({
          ...s,
          status: results[i].ok ? "ok" : "error",
          latency: results[i].latency,
        }))
      );
      
      // Fetch AI Providers specifically from user's Workspace Settings
      try {
        const res = await workspacesApi.getSettings();
        const config = res.data.ai_config || {};
        const enabledProviders: Record<string, boolean> = {};
        
        // Map keys to pretty labels for hardcoded providers
        const labelMap: Record<string, string> = {
          gemini: "Gemini",
          anthropic: "Claude",
          ollama: "Ollama",
          openai: "OpenAI"
        };

        if (config.providers) {
          Object.entries(config.providers).forEach(([key, val]: any) => {
             // Only show providers that are actually enabled in settings
             if (val && val.enabled) {
               const displayName = val.label || labelMap[key] || key;
               enabledProviders[displayName] = true;
             }
          });
        }
        
        // Also support old flat schema just in case
        if (!config.providers) {
          if (config.gemini_api_key) enabledProviders["Gemini"] = true;
          if (config.anthropic_api_key) enabledProviders["Claude"] = true;
          if (config.ollama_url) enabledProviders["Ollama"] = true;
        }

        setAiProviders(enabledProviders);
      } catch (e) {
        // Ignore error
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  const { data: recentScans } = useQuery({
    queryKey: ["scan-sessions", "recent", project?.id, assetId],
    queryFn: () => scanSessionsApi.list(project!.id, { 
      size: 5,
      asset_id: assetId !== "all" ? assetId : undefined
    }).then((r) => r.data),
    refetchInterval: 30000,
    enabled: !!project,
  });

  const { data: matrix } = useQuery({
    queryKey: ["risks", "matrix", project?.id, assetId],
    queryFn: () => risksApi.getMatrix(project?.id, assetId !== "all" ? assetId : undefined).then((r) => r.data),
  });

  const totalRisks = matrix?.summary?.total ?? 0;
  const criticalRisks = matrix?.summary?.critical ?? 0;
  const highRisks = matrix?.summary?.high ?? 0;

  const scanStats = {
    total: recentScans?.total ?? 0,
    completed: recentScans?.items?.filter((s: any) => s.status === "completed").length ?? 0,
    running: recentScans?.items?.filter((s: any) => s.status === "running").length ?? 0,
    failed: recentScans?.items?.filter((s: any) => s.status === "failed").length ?? 0,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Monitoreo</h1>
        <p className="text-sm text-gray-500 mt-0.5">Estado de los servicios y métricas operativas</p>
      </div>

      {/* Service health */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Activity size={16} className="text-gray-400" />
          Estado de Servicios
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {services.map((svc) => (
            <div key={svc.name} className="border border-gray-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-gray-600">
                  {svc.icon}
                  <span className="text-sm font-medium">{svc.name}</span>
                </div>
                {svc.status === "checking" ? (
                  <Clock size={16} className="text-gray-300 animate-pulse" />
                ) : svc.status === "ok" ? (
                  <CheckCircle size={16} className="text-green-500" />
                ) : (
                  <XCircle size={16} className="text-red-500" />
                )}
              </div>
              <div className={`text-xs font-semibold rounded-full px-2 py-0.5 inline-flex items-center gap-1 ${
                svc.status === "ok"
                  ? "bg-green-50 text-green-700"
                  : svc.status === "error"
                  ? "bg-red-50 text-red-700"
                  : "bg-gray-100 text-gray-500"
              }`}>
                <div className={`w-1.5 h-1.5 rounded-full ${
                  svc.status === "ok" ? "bg-green-500 animate-pulse" :
                  svc.status === "error" ? "bg-red-500" : "bg-gray-400"
                }`} />
                {svc.status === "ok" ? "Operativo" : svc.status === "error" ? "Sin respuesta" : "Verificando"}
              </div>
              {svc.latency !== undefined && (
                <p className="text-xs text-gray-400 mt-2">{svc.latency} ms</p>
              )}
            </div>
          ))}
          
          {/* Tarjetas inyectadas estáticamente para Postgres y Redis basadas en Backend */}
          <div className="border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-gray-600">
                <Database size={16} />
                <span className="text-sm font-medium">PostgreSQL</span>
              </div>
              {dbStatus.postgres === "checking" ? (
                <Clock size={16} className="text-gray-300 animate-pulse" />
              ) : dbStatus.postgres === "ok" ? (
                <CheckCircle size={16} className="text-green-500" />
              ) : (
                <XCircle size={16} className="text-red-500" />
              )}
            </div>
            <div className={`text-xs font-semibold rounded-full px-2 py-0.5 inline-flex items-center gap-1 ${
              dbStatus.postgres === "ok" ? "bg-green-50 text-green-700" :
              dbStatus.postgres === "error" ? "bg-red-50 text-red-700" : "bg-gray-100 text-gray-500"
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${dbStatus.postgres === "ok" ? "bg-green-500 animate-pulse" : dbStatus.postgres === "error" ? "bg-red-500" : "bg-gray-400"}`} />
              {dbStatus.postgres === "ok" ? "Operativo" : dbStatus.postgres === "error" ? "Error de conexión" : "Verificando"}
            </div>
          </div>
          
          <div className="border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-gray-600">
                <Activity size={16} />
                <span className="text-sm font-medium">Redis / Workers</span>
              </div>
              {dbStatus.redis === "checking" ? (
                <Clock size={16} className="text-gray-300 animate-pulse" />
              ) : dbStatus.redis === "ok" ? (
                <CheckCircle size={16} className="text-green-500" />
              ) : (
                <XCircle size={16} className="text-red-500" />
              )}
            </div>
            <div className={`text-xs font-semibold rounded-full px-2 py-0.5 inline-flex items-center gap-1 ${
              dbStatus.redis === "ok" ? "bg-green-50 text-green-700" :
              dbStatus.redis === "error" ? "bg-red-50 text-red-700" : "bg-gray-100 text-gray-500"
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${dbStatus.redis === "ok" ? "bg-green-500 animate-pulse" : dbStatus.redis === "error" ? "bg-red-500" : "bg-gray-400"}`} />
              {dbStatus.redis === "ok" ? "Operativo" : dbStatus.redis === "error" ? "Error de conexión" : "Verificando"}
            </div>
          </div>
          {Object.entries(aiProviders).map(([providerName, isActive]) => (
            <div key={`ai-${providerName}`} className="border border-gray-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-gray-600">
                  <ShieldAlert size={16} />
                  <span className="text-sm font-medium capitalize">AI: {providerName}</span>
                </div>
                {isActive === "checking" ? (
                  <Clock size={16} className="text-gray-300 animate-pulse" />
                ) : isActive ? (
                  <CheckCircle size={16} className="text-green-500" />
                ) : (
                  <XCircle size={16} className="text-red-500" />
                )}
              </div>
              <div className={`text-xs font-semibold rounded-full px-2 py-0.5 inline-flex items-center gap-1 ${
                isActive === "checking"
                  ? "bg-gray-100 text-gray-500"
                  : isActive
                  ? "bg-green-50 text-green-700"
                  : "bg-red-50 text-red-700"
              }`}>
                <div className={`w-1.5 h-1.5 rounded-full ${
                  isActive === "checking" ? "bg-gray-400" :
                  isActive ? "bg-green-500 animate-pulse" : "bg-red-500"
                }`} />
                {isActive === "checking" ? "Verificando" : isActive ? "Activado" : "Error / Apagado"}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Dynamic Scanners Manager */}
      <ScannersManager />

    </div>
  );
}
