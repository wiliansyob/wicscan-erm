"use client";
import { cn, RISK_BG_COLORS, STATUS_COLORS } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "risk" | "status" | "default";
  level?: string;
  className?: string;
}

export function Badge({ children, variant = "default", level, className }: BadgeProps) {
  let colorClass = "bg-gray-500/10 border-gray-500/30 text-gray-400";

  if (variant === "risk" && level) {
    colorClass = RISK_BG_COLORS[level.toLowerCase()] ?? colorClass;
  } else if (variant === "status" && level) {
    colorClass = STATUS_COLORS[level.toLowerCase()] ?? colorClass;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border",
        colorClass,
        className
      )}
    >
      {children}
    </span>
  );
}
