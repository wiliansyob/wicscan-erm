"use client";

import { ShieldAlert, ShieldX, Shield, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface SummaryCardsProps {
  data: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
    under_treatment: number;
  };
}

const CARDS = [
  {
    key: "critical" as const,
    label: "Crítico",
    icon: ShieldX,
    color: "text-red-600",
    bg: "bg-red-50 border-red-200",
    iconBg: "bg-red-100",
  },
  {
    key: "high" as const,
    label: "Alto",
    icon: ShieldAlert,
    color: "text-orange-600",
    bg: "bg-orange-50 border-orange-200",
    iconBg: "bg-orange-100",
  },
  {
    key: "medium" as const,
    label: "Medio",
    icon: Shield,
    color: "text-yellow-600",
    bg: "bg-yellow-50 border-yellow-200",
    iconBg: "bg-yellow-100",
  },
  {
    key: "under_treatment" as const,
    label: "En Tratamiento",
    icon: TrendingUp,
    color: "text-blue-600",
    bg: "bg-blue-50 border-blue-200",
    iconBg: "bg-blue-100",
  },
];

export function RiskSummaryCards({ data }: SummaryCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4">
      {CARDS.map(({ key, label, icon: Icon, color, bg, iconBg }) => (
        <div key={key} className={cn("rounded-xl border p-4", bg)}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
            <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", iconBg)}>
              <Icon size={14} className={color} />
            </div>
          </div>
          <p className={cn("text-3xl font-bold", color)}>{data[key]}</p>
          <p className="text-xs text-gray-400 mt-1">
            {data.total > 0 ? `${Math.round((data[key] / data.total) * 100)}% del total` : "Sin riesgos"}
          </p>
        </div>
      ))}
    </div>
  );
}
