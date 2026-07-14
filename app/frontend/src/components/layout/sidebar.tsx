"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ScanLine,
  BarChart3,
  ShieldCheck,
  FileText,
  Activity,
  Settings,
  LogOut,
  ShieldAlert,
  FolderOpen,
  ChevronRight,
  ArrowLeftRight,
  ShieldAlert as ShieldAlertIcon,
  Code2,
  ExternalLink,
  Percent,
  Zap,
  TrendingUp,
  HardDrive,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/auth";
import { useProjectStore } from "@/lib/project";
import { projectsApi } from "@/lib/api";

const NAV_ITEMS = [
  { label: "GESTIÓN DE RIESGOS", isGroup: true },

  { label: "Fase 1: Contextualización", isPhase: true },
  { href: "/contexto/bia",   label: "Procesos de negocio", icon: TrendingUp,      isGroup: false, soon: false },

  { label: "Fase 2: Identificación", isPhase: true },
  { href: "/activos",        label: "Activos",             icon: HardDrive,       isGroup: false, soon: false },
  { href: "/scans",          label: "Vulnerabilidades",    icon: ScanLine,        isGroup: false, soon: false },

  { label: "Fase 3: Analisis", isPhase: true },
  { href: "/escenarios",     label: "Escenarios",          icon: ShieldAlertIcon, isGroup: false, soon: false },
  { href: "/probabilidad",   label: "Probabilidad",        icon: Percent,         isGroup: false, soon: false },
  { href: "/impacto",        label: "Impacto",             icon: Zap,             isGroup: false, soon: false },

  { label: "Fase 4: Evaluación", isPhase: true },
  { href: "/analisis",       label: "Riesgos",             icon: BarChart3,       isGroup: false, soon: false },

  { label: "Fase 5: Tratamiento", isPhase: true },
  { href: "/tratamiento",    label: "Tratamiento",         icon: ShieldCheck,     isGroup: false, soon: false },
  { href: "/reporte",        label: "Reporte",             icon: FileText,        isGroup: false, soon: false },
];

const SYSTEM_ITEMS = [
  { href: "/monitoring",         label: "Monitoreo",      icon: Activity },
  { href: "/settings",           label: "Configuración",  icon: Settings },
];

const APPETITE_COLORS: Record<string, string> = {
  low:      "bg-blue-100 text-blue-700",
  medium:   "bg-yellow-100 text-yellow-700",
  high:     "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

const APPETITE_LABELS: Record<string, string> = {
  low: "Bajo", medium: "Medio", high: "Alto", critical: "Crítico",
};

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuthStore();
  const { project, setProject, clearProject } = useProjectStore();

  // Keep sidebar counts in sync with the DB (refetch every 30s and on window focus)
  useQuery({
    queryKey: ["project-live", project?.id],
    queryFn: async () => {
      const res = await projectsApi.get(project!.id);
      setProject(res.data);
      return res.data;
    },
    enabled: !!project?.id,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    staleTime: 15_000,
  });

  const handleLogout = () => {
    clearProject();
    logout();
    router.push("/login");
  };

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0 flex-shrink-0">
      {/* Logo */}
      <div className="p-5 border-b border-gray-100">
        <Link href="/projects" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
            <ShieldAlert size={16} className="text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-gray-900 font-bold text-sm leading-none">WicScan</p>
            <p className="text-gray-400 text-xs mt-0.5">Risk Manager</p>
          </div>
        </Link>
      </div>

      {/* Proyecto activo */}
      <div className="px-3 py-3 border-b border-gray-100">
        {project ? (
          <button
            onClick={() => router.push("/projects")}
            className="w-full flex items-start gap-2.5 p-2.5 rounded-lg bg-blue-50 border border-blue-100 hover:bg-blue-100 transition-all text-left group"
          >
            <FolderOpen size={14} className="text-blue-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-blue-800 truncate">{project.name}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={cn("text-xs px-1.5 py-0 rounded font-medium", APPETITE_COLORS[project.risk_appetite])}>
                  {APPETITE_LABELS[project.risk_appetite] ?? project.risk_appetite}
                </span>
                <span className="text-xs text-blue-400">{project.open_risk_count} riesgos</span>
              </div>
            </div>
            <ArrowLeftRight size={11} className="text-blue-400 mt-0.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        ) : (
          <Link
            href="/projects"
            className="flex items-center gap-2 px-2.5 py-2 rounded-lg border border-dashed border-gray-300 text-gray-400 hover:border-blue-300 hover:text-blue-600 transition-all text-xs"
          >
            <FolderOpen size={13} />
            <span>Seleccionar proyecto</span>
          </Link>
        )}
      </div>

      {/* Navegación */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item, idx) => {
          const { label } = item;
          const { href, icon: Icon, isGroup, isPhase, soon } = item as any;

          if (isGroup) {
            return (
              <p key={`group-${idx}`} className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 pb-2 pt-1">
                {label}
              </p>
            );
          }

          if (isPhase) {
            return (
              <p key={`phase-${idx}`} className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider px-3 pb-1 pt-3">
                {label}
              </p>
            );
          }

          if (soon) {
            return (
              <div
                key={href || idx}
                className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm cursor-default text-gray-300"
              >
                <div className="w-5 h-5 rounded flex items-center justify-center bg-gray-50 flex-shrink-0">
                  <Icon size={12} className="text-gray-300" />
                </div>
                <span className="font-medium flex-1">{label}</span>
                <span className="text-[9px] bg-gray-100 text-gray-400 rounded px-1.5 py-0.5 font-medium">pronto</span>
              </div>
            );
          }

          const active = href && (pathname === href || pathname.startsWith(href + "/"));
          const disabled = !project;
          return (
            <Link
              key={href || idx}
              href={disabled ? "/projects" : (href as string)}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group",
                active && !disabled
                  ? "bg-blue-50 text-blue-700 border border-blue-100"
                  : disabled
                  ? "text-gray-300 cursor-not-allowed pointer-events-none"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              )}
            >
              <div className={cn(
                "w-5 h-5 rounded flex items-center justify-center text-xs font-bold flex-shrink-0",
                active && !disabled ? "bg-blue-600 text-white" :
                disabled ? "bg-gray-100 text-gray-300" :
                "bg-gray-100 text-gray-500 group-hover:bg-gray-200"
              )}>
                {Icon && <Icon size={13} />}
              </div>
              <span className="font-medium">{label}</span>
              {active && !disabled && <ChevronRight size={11} className="ml-auto text-blue-400" />}
            </Link>
          );
        })}

        <div className="pt-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 pb-2">Sistema</p>
          {SYSTEM_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group",
                  active
                    ? "bg-blue-50 text-blue-700 border border-blue-100"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                )}
              >
                <Icon size={15} className={cn(active ? "text-blue-600" : "text-gray-400 group-hover:text-gray-600")} />
                <span className="font-medium">{label}</span>
                {active && <ChevronRight size={11} className="ml-auto text-blue-400" />}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer / External Tools */}
      <div className="p-3 border-t border-gray-100 flex flex-col gap-1">

        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 w-full transition-all mt-1 border-t border-gray-50 pt-2"
        >
          <LogOut size={15} />
          <span>Cerrar sesión</span>
        </button>
      </div>
    </aside>
  );
}
