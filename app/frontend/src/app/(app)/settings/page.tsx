"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/auth";
import { User, Building2, Key, Shield, Bell, ChevronRight, Save, Loader2, BrainCircuit, Copy, Check, Plus, Trash2, FileText, Code, AlertTriangle, LibraryBig, Clock, Archive, ExternalLink } from "lucide-react";
import { workspacesApi } from "@/lib/api";
import { catalogApi, type DefinitionOut } from "@/lib/api/admin";

const SECTIONS = [
  { id: "profile",       label: "Perfil de Usuario", icon: User },
  { id: "security",      label: "Seguridad",           icon: Shield },
  { id: "api",           label: "Claves API",          icon: Key },
  { id: "prompts",       label: "Prompts IA",          icon: BrainCircuit },
  { id: "reports",       label: "Reportes",            icon: FileText },
  { id: "questionnaire", label: "Cuestionario",        icon: LibraryBig },
];

const DEFAULT_SCANNER_PROMPT = `You are a static application security testing (SAST) engine. Your task is to analyse a source-code snippet for security vulnerabilities.

Return ONLY a JSON array — no prose, no markdown, no code fences. Each element must follow this schema exactly:

{
  "rule_id":     "<snake_case identifier, e.g. sql_injection>",
  "title":       "<one-line description>",
  "description": "<explanation of the vulnerability and why it is dangerous>",
  "severity":    "critical" | "high" | "medium" | "low" | "info",
  "category":    "<OWASP-aligned category, e.g. sql_injection, xss, hardcoded_credentials>",
  "cwe":         "<CWE-NNN or null>",
  "owasp":       "<OWASP Top 10 ID, e.g. A03 or null>",
  "line":        <integer line number or null>,
  "snippet":     "<the problematic code (max 120 chars) or null>",
  "remediation": "<how to fix the vulnerability>"
}

Rules:
- Report ONLY vulnerabilities that are clearly visible in the provided code.
- Do NOT speculate about code that is not shown.
- Do NOT report style issues, deprecated APIs, or performance concerns.
- If the code has no security vulnerabilities, return an empty array: []
- Output must be valid JSON: no comments, no trailing commas, no extra text.`;

const PROMPT_TEMPLATES = [
  {
    id: "iso_31000",
    label: "ISO 31000",
    badge: "Por defecto",
    badgeColor: "bg-blue-50 text-blue-700 border-blue-200",
    description: "Análisis de riesgo alineado a ISO 31000. Evalúa probabilidad e impacto desde la perspectiva de negocio, considerando criticidad del activo, exposición y clasificación de datos.",
    content: `Eres un experto Analista de Riesgos de Seguridad especializado en gestión de riesgos ISO 31000.

Tu rol es analizar hallazgos de seguridad en aplicaciones y producir evaluaciones de riesgo estructuradas que apoyen la toma de decisiones del negocio.

REGLAS CRÍTICAS:
1. NUNCA analizas código fuente crudo — solo metadatos estructurados de hallazgos
2. SIEMPRE produces JSON válido con el esquema requerido
3. Puntúas probabilidad e impacto en escala 1-9
4. Consideras el contexto de negocio, no solo la severidad técnica
5. TODO el texto de análisis y recomendaciones en español

GUÍA DE PUNTUACIÓN (ISO 31000):
- Probabilidad: 1=Prácticamente imposible, 3=Difícil, 5=Moderada, 7=Fácil, 9=Segura
- Impacto: 1=Daño mínimo, 3=Daño financiero menor, 5=Daño significativo, 7=Daño financiero grande, 9=Daño crítico`,
  },
  {
    id: "owasp_top_10",
    label: "OWASP Top 10",
    badge: "OWASP RRM",
    badgeColor: "bg-orange-50 text-orange-700 border-orange-200",
    description: "Análisis técnico siguiendo el OWASP Risk Rating Methodology. Pondera factores de agente de amenaza, facilidad de explotación, prevalencia e impacto técnico y de negocio.",
    content: `Eres un Ingeniero de Seguridad altamente técnico especializado en el framework OWASP Top 10 y la Metodología de Calificación de Riesgos OWASP (RRM).

Tu rol es analizar vulnerabilidades de aplicaciones web siguiendo las guías OWASP estrictamente.

REGLAS CRÍTICAS:
1. NUNCA analizas código fuente crudo — solo metadatos estructurados de hallazgos
2. SIEMPRE produces JSON válido con el esquema requerido
3. Puntúas probabilidad e impacto en escala 1-9 usando factores OWASP
4. Tu análisis DEBE referenciar explícitamente categorías OWASP Top 10 (ej. A01:2021-Broken Access Control)
5. TODO el texto en español

FACTORES OWASP para PROBABILIDAD:
- Agente de amenaza: motivación, capacidad, tamaño del grupo
- Vulnerabilidad: facilidad de descubrimiento, facilidad de explotación, prevalencia

FACTORES OWASP para IMPACTO:
- Impacto técnico: pérdida de confidencialidad, integridad, disponibilidad, accountability
- Impacto de negocio: daño financiero, reputacional, cumplimiento normativo`,
  },
  {
    id: "nist_800_30",
    label: "NIST SP 800-30",
    badge: "NIST",
    badgeColor: "bg-purple-50 text-purple-700 border-purple-200",
    description: "Evaluación de riesgos siguiendo la guía NIST SP 800-30. Analiza fuentes de amenaza, eventos de amenaza, vulnerabilidades y condiciones predisponentes de forma rigurosa.",
    content: `Eres un Evaluador Senior de Riesgos Cibernéticos especializado en NIST SP 800-30 Guía para Conducir Evaluaciones de Riesgos.

Tu rol es evaluar amenazas, vulnerabilidades e impactos siguiendo el riguroso framework NIST.

REGLAS CRÍTICAS:
1. NUNCA analizas código fuente crudo — solo metadatos estructurados de hallazgos
2. SIEMPRE produces JSON válido con el esquema requerido
3. Puntúas probabilidad (probabilidad de iniciación + probabilidad de éxito) e impacto en escala 1-9
4. Debes enfocarte en Fuentes de Amenaza, Eventos de Amenaza, Vulnerabilidades y Condiciones Predisponentes
5. TODO el texto en español

TAXONOMÍA NIST SP 800-30:
- Fuentes de Amenaza: Adversarial / Accidental / Estructural / Ambiental
- Características: Capacidad, Intención, Objetivo (para adversariales)
- Relevancia de Vulnerabilidad: Alta / Media / Baja
- Predisposición: Muy Alta / Alta / Moderada / Baja / Muy Baja`,
  },
];

const STATUS_META: Record<string, { label: string; cls: string; Icon: React.ElementType }> = {
  draft:     { label: "Borrador",  cls: "bg-yellow-100 text-yellow-700", Icon: Clock },
  published: { label: "Publicada", cls: "bg-green-100 text-green-700",  Icon: Check },
  archived:  { label: "Archivada", cls: "bg-gray-100 text-gray-500",    Icon: Archive },
};

export default function SettingsPage() {
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const [active, setActive] = useState("profile");
  
  const [aiConfig, setAiConfig] = useState<any>({
    providers: {
      ollama: { enabled: false, url: "http://ollama:11434" },
      anthropic: { enabled: false, api_key: "" },
      gemini: { enabled: false, api_key: "" }
    },
    prompts: PROMPT_TEMPLATES,
    report_config: { objective: "", scope: "" }
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const { data: definitions = [], isLoading: isLoadingDefs } = useQuery<DefinitionOut[]>({
    queryKey: ["questionnaire-definitions"],
    queryFn: () => catalogApi.list().then((r) => r.data),
    enabled: active === "questionnaire",
  });

  const createDefMutation = useMutation({
    mutationFn: () => catalogApi.create(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["questionnaire-definitions"] }),
  });

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  useEffect(() => {
    setLoading(true);
    workspacesApi.getSettings()
      .then(res => {
        const config = res.data.ai_config || {};
        const mergedProviders: Record<string, any> = {
            ollama: { enabled: false, url: "http://ollama:11434", model: "llama3.2", ...config.providers?.ollama },
            anthropic: { enabled: false, api_key: "", url: "https://api.anthropic.com", model: "claude-3-5-sonnet-20241022", ...config.providers?.anthropic },
            gemini: { enabled: false, api_key: "", url: "https://generativelanguage.googleapis.com/v1beta", model: "gemini-flash-latest", ...config.providers?.gemini }
        };
        // Backwards compatibility with old flat schema
        if (config.anthropic_api_key) mergedProviders.anthropic.api_key = config.anthropic_api_key;
        if (config.gemini_api_key) mergedProviders.gemini.api_key = config.gemini_api_key;
        // Restore custom providers saved in DB
        Object.entries(config.providers || {}).forEach(([key, value]) => {
          if (key.startsWith("custom_")) mergedProviders[key] = value;
        });

        setAiConfig({
            providers: mergedProviders,
            prompts: config.prompts && config.prompts.length > 0 ? config.prompts : PROMPT_TEMPLATES,
            scanner_prompt: config.scanner_prompt || DEFAULT_SCANNER_PROMPT,
            report_config: config.report_config || { objective: "", scope: "" }
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSaveKeys = async () => {
    setSaving(true);
    setMessage("");
    try {
      await workspacesApi.updateSettings({ ai_config: aiConfig });
      setMessage("Configuración guardada exitosamente.");
    } catch (err) {
      setMessage("Error al guardar la configuración.");
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(""), 3000);
    }
  };

  const updateProvider = (key: string, field: string, value: any) => {
    setAiConfig((prev: any) => ({
      ...prev,
      providers: {
        ...prev.providers,
        [key]: {
          ...prev.providers[key],
          [field]: value
        }
      }
    }));
  };

  const updateReportConfig = (field: string, value: string) => {
    setAiConfig((prev: any) => ({
      ...prev,
      report_config: {
        ...prev.report_config,
        [field]: value
      }
    }));
  };

  const addCustomProvider = () => {
    const id = `custom_${Date.now()}`;
    setAiConfig((prev: any) => ({
      ...prev,
      providers: {
        ...prev.providers,
        [id]: {
          enabled: true,
          label: "Mi Proveedor Personalizado",
          url: "https://api.groq.com/openai/v1",
          model: "llama3-8b-8192",
          api_key: "",
          is_custom: true
        }
      }
    }));
  };

  const removeCustomProvider = (key: string) => {
    setAiConfig((prev: any) => {
      const nextProviders = { ...prev.providers };
      delete nextProviders[key];
      return { ...prev, providers: nextProviders };
    });
  };

  const updatePrompt = (id: string, newContent: string) => {
    setAiConfig((prev: any) => ({
      ...prev,
      prompts: prev.prompts.map((p: any) => p.id === id ? { ...p, content: newContent } : p)
    }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configuración</h1>
        <p className="text-sm text-gray-500 mt-0.5">Administra tu cuenta y preferencias de la plataforma</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <aside className="w-52 flex-shrink-0">
          <nav className="space-y-0.5">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActive(id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all text-left ${
                  active === id
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}
              >
                <Icon size={15} className={active === id ? "text-blue-600" : "text-gray-400"} />
                {label}
                {active === id && <ChevronRight size={12} className="ml-auto text-blue-400" />}
              </button>
            ))}
          </nav>
        </aside>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {active === "profile" && (
            <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
              <h2 className="text-base font-semibold text-gray-900">Perfil de Usuario</h2>
              <div className="flex items-center gap-4 pb-5 border-b border-gray-100">
                <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-xl font-bold">
                  {user?.full_name?.charAt(0)?.toUpperCase() ?? "U"}
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{user?.full_name ?? "—"}</p>
                  <p className="text-sm text-gray-500">{user?.email ?? "—"}</p>
                  <span className="text-xs bg-blue-50 text-blue-700 border border-blue-100 rounded px-2 py-0.5 mt-1 inline-block">
                    CISO
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Nombre completo</label>
                  <input
                    readOnly
                    value={user?.full_name ?? ""}
                    className="w-full bg-gray-50 border border-gray-200 text-gray-700 rounded-lg px-3 py-2 text-sm cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Correo electrónico</label>
                  <input
                    readOnly
                    value={user?.email ?? ""}
                    className="w-full bg-gray-50 border border-gray-200 text-gray-700 rounded-lg px-3 py-2 text-sm cursor-not-allowed"
                  />
                </div>
              </div>
              <p className="text-xs text-gray-400">La edición de perfil estará disponible próximamente.</p>
            </div>
          )}



          {active === "security" && (
            <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
              <h2 className="text-base font-semibold text-gray-900">Seguridad</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-200">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Contraseña</p>
                    <p className="text-xs text-gray-400 mt-0.5">Última modificación: no disponible</p>
                  </div>
                  <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">Cambiar</button>
                </div>
              </div>
              <p className="text-xs text-gray-400">Esta funcionalidad estará disponible próximamente.</p>
            </div>
          )}

          {active === "api" && (
            <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-gray-900">Claves de Inteligencia Artificial</h2>
                <button 
                  onClick={handleSaveKeys}
                  disabled={saving || loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                  Guardar Cambios
                </button>
              </div>
              
              {message && (
                <div className={`p-3 rounded-lg text-sm ${message.includes("Error") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
                  {message}
                </div>
              )}

              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-xl text-sm text-yellow-800">
                Las claves API permiten habilitar los diferentes motores de Inteligencia Artificial. Se guardan de forma segura en tu Workspace.
              </div>
              
              <div className="space-y-4">
                {/* Ollama Local */}
                <div className="p-4 border border-gray-200 rounded-xl bg-gray-50 relative overflow-hidden">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-900 mb-1">Ollama API</label>
                      <p className="text-xs text-gray-500">Configura la URL para usar IA local y privada (Gratis).</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" checked={aiConfig.providers.ollama?.enabled} onChange={(e) => updateProvider("ollama", "enabled", e.target.checked)} className="sr-only peer" />
                      <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <label className="block text-xs font-medium text-gray-500 mb-1">API URL (Base)</label>
                      <input
                        type="text"
                        placeholder="http://ollama:11434"
                        value={aiConfig.providers.ollama?.url || ""}
                        onChange={(e) => updateProvider("ollama", "url", e.target.value)}
                        disabled={!aiConfig.providers.ollama?.enabled}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="block text-xs font-medium text-gray-500 mb-1">Modelo(s) (separados por coma)</label>
                      <input
                        type="text"
                        placeholder="llama3.2"
                        value={aiConfig.providers.ollama?.model || ""}
                        onChange={(e) => updateProvider("ollama", "model", e.target.value)}
                        disabled={!aiConfig.providers.ollama?.enabled}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100 font-mono"
                      />
                    </div>
                  </div>
                </div>

                {/* Others */}
                {[
                  { id: "anthropic", label: "Claude API Key", hint: "Requerida para análisis con la familia Claude 3.5 Sonnet", defaultUrl: "https://api.anthropic.com", defaultModel: "claude-3-5-sonnet-20241022" },
                  { id: "gemini", label: "Gemini API Key", hint: "Requerida para análisis con Google Gemini Pro", defaultUrl: "https://generativelanguage.googleapis.com/v1beta", defaultModel: "gemini-flash-latest" },
                ].map(({ id, label, hint, defaultUrl, defaultModel }) => (
                  <div key={id} className="p-4 border border-gray-200 rounded-xl bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-900 mb-1">{label}</label>
                        <p className="text-xs text-gray-500">{hint}</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" checked={aiConfig.providers[id]?.enabled} onChange={(e) => updateProvider(id, "enabled", e.target.checked)} className="sr-only peer" />
                        <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    <div className="space-y-3 mt-4">
                      <div className="flex gap-4">
                        <div className="flex-1">
                          <label className="block text-xs font-medium text-gray-500 mb-1">API URL (Base)</label>
                          <input
                            type="text"
                            placeholder={defaultUrl}
                            value={aiConfig.providers[id]?.url || ""}
                            onChange={(e) => updateProvider(id, "url", e.target.value)}
                            disabled={!aiConfig.providers[id]?.enabled}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100 font-mono"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs font-medium text-gray-500 mb-1">Modelo(s) (separados por coma)</label>
                          <input
                            type="text"
                            placeholder={defaultModel}
                            value={aiConfig.providers[id]?.model || ""}
                            onChange={(e) => updateProvider(id, "model", e.target.value)}
                            disabled={!aiConfig.providers[id]?.enabled}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100 font-mono"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">API Key (Token Secreto)</label>
                        <input
                          type="password"
                          autoComplete="current-password"
                          placeholder="sk-..."
                          value={aiConfig.providers[id]?.api_key || ""}
                          onChange={(e) => updateProvider(id, "api_key", e.target.value)}
                          disabled={!aiConfig.providers[id]?.enabled}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100 font-mono"
                        />
                      </div>
                    </div>
                  </div>
                ))}
                
                {/* Custom Providers */}
                {Object.keys(aiConfig.providers || {}).filter(k => k.startsWith("custom_")).map(id => (
                  <div key={id} className="p-4 border border-blue-200 rounded-xl bg-blue-50/30 relative">
                    <button 
                      onClick={() => removeCustomProvider(id)}
                      className="absolute top-4 right-4 text-gray-400 hover:text-red-600 transition-colors"
                      title="Eliminar proveedor"
                    >
                      <Trash2 size={16} />
                    </button>
                    <div className="flex items-center justify-between mb-3 pr-10">
                      <div className="w-full max-w-sm">
                        <label className="block text-sm font-medium text-gray-900 mb-1">Nombre del Proveedor</label>
                        <input
                          type="text"
                          placeholder="Ej. Groq o Mistral"
                          value={aiConfig.providers[id]?.label || ""}
                          onChange={(e) => updateProvider(id, "label", e.target.value)}
                          className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                        />
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer mt-5">
                        <input type="checkbox" checked={aiConfig.providers[id]?.enabled} onChange={(e) => updateProvider(id, "enabled", e.target.checked)} className="sr-only peer" />
                        <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    <div className="space-y-3 mt-4">
                      <div className="flex gap-4">
                        <div className="flex-1">
                          <label className="block text-xs font-medium text-gray-500 mb-1">API URL (Compatible)</label>
                          <input
                            type="text"
                            placeholder="https://api.groq.com/openai/v1"
                            value={aiConfig.providers[id]?.url || ""}
                            onChange={(e) => updateProvider(id, "url", e.target.value)}
                            disabled={!aiConfig.providers[id]?.enabled}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100 font-mono bg-white"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs font-medium text-gray-500 mb-1">Modelo(s) (separados por coma)</label>
                          <input
                            type="text"
                            placeholder="llama3-8b-8192"
                            value={aiConfig.providers[id]?.model || ""}
                            onChange={(e) => updateProvider(id, "model", e.target.value)}
                            disabled={!aiConfig.providers[id]?.enabled}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100 font-mono bg-white"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">API Key (Token Secreto)</label>
                        <input
                          type="password"
                          autoComplete="current-password"
                          placeholder="gsk_..."
                          value={aiConfig.providers[id]?.api_key || ""}
                          onChange={(e) => updateProvider(id, "api_key", e.target.value)}
                          disabled={!aiConfig.providers[id]?.enabled}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100 font-mono bg-white"
                        />
                      </div>
                    </div>
                  </div>
                ))}

                <button
                  onClick={addCustomProvider}
                  className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-sm font-medium text-gray-600 hover:text-blue-600 hover:border-blue-400 hover:bg-blue-50 transition-colors flex items-center justify-center gap-2"
                >
                  <Plus size={18} />
                  Añadir nuevo proveedor compatible
                </button>
              </div>
            </div>
          )}

          {active === "prompts" && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-gray-900">Prompts de Análisis IA</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Plantillas de sistema usadas por el motor de riesgos. Puedes modificarlas directamente.
                  </p>
                </div>
                <button 
                  onClick={handleSaveKeys}
                  disabled={saving || loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                  Guardar Cambios
                </button>
              </div>

              {message && (
                <div className={`p-3 rounded-lg text-sm ${message.includes("Error") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
                  {message}
                </div>
              )}

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-sm text-blue-700">
                Estos prompts se envían junto con los hallazgos del escáner y el contexto de negocio (README) de cada aplicación. 
                Si editas el contenido aquí y haces clic en "Guardar Cambios", la IA empezará a usar las nuevas reglas inmediatamente.
              </div>

              <div className="space-y-4">
                {/* Scanner Prompt */}
                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-purple-500 transition-shadow">
                  <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between bg-purple-50/50">
                    <div className="flex items-center gap-3">
                      <Code size={16} className="text-purple-600" />
                      <span className="text-sm font-semibold text-gray-900">Escáner SAST IA</span>
                      <span className="text-xs px-2 py-0.5 rounded-full border font-medium bg-purple-100 text-purple-700 border-purple-200">
                        Fase: Escaneo de Código
                      </span>
                    </div>
                  </div>
                  <div className="px-5 py-3 border-b border-gray-100 bg-yellow-50/50">
                    <p className="text-xs text-yellow-800 font-medium flex items-center gap-1.5 mb-1">
                      <AlertTriangle size={14} /> Advertencia Crítica
                    </p>
                    <p className="text-[11px] text-yellow-700">
                      Este prompt instruye a la IA para analizar código fuente crudo. <strong>DEBE</strong> retornar estrictamente un JSON array con la estructura esperada por el backend. Modifica las reglas de negocio, pero no elimines las instrucciones de formato JSON o el escáner fallará. (Déjalo en blanco para usar el default).
                    </p>
                  </div>
                  <div className="p-0">
                    <textarea
                      value={aiConfig.scanner_prompt || ""}
                      onChange={(e) => setAiConfig((prev: any) => ({ ...prev, scanner_prompt: e.target.value }))}
                      placeholder="Deja en blanco para usar el prompt por defecto del sistema..."
                      rows={12}
                      className="w-full border-0 px-5 py-4 text-xs font-mono text-gray-700 leading-relaxed focus:ring-0 resize-y"
                    />
                  </div>
                </div>

                {aiConfig.prompts?.map((pt: any) => (
                  <div key={pt.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 transition-shadow">
                    <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50">
                      <div className="flex items-center gap-3">
                        <BrainCircuit size={16} className="text-gray-400" />
                        <span className="text-sm font-semibold text-gray-900">{pt.label}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${pt.badgeColor}`}>
                          {pt.badge}
                        </span>
                      </div>
                    </div>
                    <div className="px-5 py-3 border-b border-gray-100">
                      <p className="text-xs text-gray-500">{pt.description}</p>
                    </div>
                    <div className="p-0">
                      <textarea
                        value={pt.content}
                        onChange={(e) => updatePrompt(pt.id, e.target.value)}
                        rows={10}
                        className="w-full border-0 px-5 py-4 text-xs font-mono text-gray-700 leading-relaxed focus:ring-0 resize-y"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {active === "reports" && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-gray-900">Configuración de Reportes</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Personaliza los textos por defecto para la generación de reportes PDF.
                  </p>
                </div>
                <button 
                  onClick={handleSaveKeys}
                  disabled={saving || loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                  Guardar Cambios
                </button>
              </div>

              {message && (
                <div className={`p-3 rounded-lg text-sm ${message.includes("Error") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
                  {message}
                </div>
              )}

              <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-6">
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">1.1 Objetivo del Análisis</label>
                  <p className="text-xs text-gray-500 mb-3">Este texto aparecerá en la sección de Introducción de todos tus reportes exportados.</p>
                  <textarea
                    value={aiConfig.report_config?.objective || ""}
                    onChange={(e) => updateReportConfig("objective", e.target.value)}
                    rows={4}
                    placeholder="Ej. El objetivo principal de este análisis es identificar, evaluar y clasificar los riesgos de seguridad..."
                    className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y"
                  />
                </div>

                <div className="pt-4 border-t border-gray-100">
                  <label className="block text-sm font-bold text-gray-900 mb-2">1.2 Alcance</label>
                  <p className="text-xs text-gray-500 mb-3">Define los límites y el enfoque de las auditorías generadas.</p>
                  <textarea
                    value={aiConfig.report_config?.scope || ""}
                    onChange={(e) => updateReportConfig("scope", e.target.value)}
                    rows={4}
                    placeholder="Ej. El alcance comprende la infraestructura técnica, aplicaciones web expuestas y..."
                    className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y"
                  />
                </div>
              </div>
            </div>
          )}

          {active === "questionnaire" && (
            <div className="space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-base font-semibold text-gray-900">Catálogo de cuestionarios</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Gestiona las plantillas del cuestionario de contextualización. Solo la versión publicada activa se usa al iniciar nuevos cuestionarios de proyecto.
                  </p>
                </div>
                <button
                  onClick={() => createDefMutation.mutate()}
                  disabled={createDefMutation.isPending}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2.5 px-5 transition-all flex-shrink-0"
                >
                  {createDefMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                  Nuevo borrador
                </button>
              </div>

              {createDefMutation.isError && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                  <AlertTriangle size={14} className="flex-shrink-0" />
                  {(createDefMutation.error as any)?.response?.data?.detail ?? "Error al crear el borrador."}
                </div>
              )}

              {isLoadingDefs ? (
                <div className="flex items-center gap-3 py-10 text-gray-400 text-sm justify-center">
                  <Loader2 size={16} className="animate-spin text-blue-500" /> Cargando…
                </div>
              ) : definitions.length === 0 ? (
                <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-10 text-center">
                  <LibraryBig size={28} className="mx-auto mb-3 text-gray-300" />
                  <p className="text-gray-500 text-sm font-medium">Sin definiciones de cuestionario</p>
                  <p className="text-gray-400 text-xs mt-1 mb-4">Crea un borrador para añadir preguntas y publicar la primera versión.</p>
                  <button
                    onClick={() => createDefMutation.mutate()}
                    disabled={createDefMutation.isPending}
                    className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl py-2.5 px-6 transition-all"
                  >
                    {createDefMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />}
                    Nuevo borrador
                  </button>
                </div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                  <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
                    <p className="text-sm font-semibold text-gray-700">Versiones del cuestionario</p>
                    <div className="flex gap-4 text-xs text-gray-500">
                      <span className="text-green-600 font-medium">{definitions.filter(d => d.status === "published").length} publicadas</span>
                      <span className="text-yellow-600 font-medium">{definitions.filter(d => d.status === "draft").length} borradores</span>
                    </div>
                  </div>
                  <ul className="divide-y divide-gray-100">
                    {definitions.map((def) => {
                      const meta = STATUS_META[def.status] ?? STATUS_META.draft;
                      return (
                        <li key={def.id} className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className="text-sm font-semibold text-gray-900">v{def.version}</span>
                              <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${meta.cls}`}>
                                <meta.Icon size={10} />
                                {meta.label}
                              </span>
                            </div>
                            <p className="text-xs text-gray-400">
                              {def.questions.length} preguntas · creado {new Date(def.created_at).toLocaleDateString("es-ES")}
                              {def.published_at && ` · publicado ${new Date(def.published_at).toLocaleDateString("es-ES")}`}
                            </p>
                          </div>
                          {def.status === "draft" && (
                            <Link
                              href={`/admin/questionnaire/${def.id}`}
                              className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-colors"
                            >
                              <ExternalLink size={12} /> Editar
                            </Link>
                          )}
                          {def.status === "published" && (
                            <div className="flex items-center gap-2">
                              <span className="flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-50 px-3 py-1.5 rounded-lg">
                                <Check size={12} /> Activa
                              </span>
                              <Link
                                href={`/admin/questionnaire/${def.id}`}
                                className="flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-lg transition-colors"
                              >
                                <ExternalLink size={12} /> Ver
                              </Link>
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-xs text-blue-700">
                <span className="font-semibold">Ciclo de vida:</span>{" "}
                Borrador → editar preguntas → Publicar (inmutable). Para revisar una versión publicada usa «Nuevo borrador» para clonar.
              </div>
            </div>
          )}

          {active === "notifications" && (
            <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
              <h2 className="text-base font-semibold text-gray-900">Notificaciones</h2>
              <div className="space-y-3">
                {[
                  { label: "Nuevos riesgos críticos", description: "Notificar cuando se detecte un riesgo crítico", enabled: true },
                  { label: "Análisis completado", description: "Notificar al finalizar un escaneo", enabled: true },
                  { label: "Tratamientos vencidos", description: "Recordatorio de planes de tratamiento vencidos", enabled: false },
                  { label: "Reporte semanal", description: "Resumen semanal del estado de riesgos", enabled: false },
                ].map(({ label, description, enabled }) => (
                  <div key={label} className="flex items-center justify-between p-4 border border-gray-200 rounded-xl">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{label}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{description}</p>
                    </div>
                    <button
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                        enabled ? "bg-blue-600" : "bg-gray-200"
                      } cursor-not-allowed opacity-60`}
                    >
                      <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
                        enabled ? "translate-x-4" : "translate-x-0.5"
                      }`} />
                    </button>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400">La configuración de notificaciones estará disponible próximamente.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
