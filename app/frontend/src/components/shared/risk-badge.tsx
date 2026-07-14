"use client";
import { Badge } from "@/components/ui/badge";

const LEVEL_LABELS: Record<string, string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Medio",
  low: "Bajo",
  info: "Info",
};

interface RiskBadgeProps {
  level: string;
  className?: string;
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  const normalized = level?.toLowerCase() ?? "";
  return (
    <Badge variant="risk" level={normalized} className={className}>
      {LEVEL_LABELS[normalized] ?? level}
    </Badge>
  );
}
