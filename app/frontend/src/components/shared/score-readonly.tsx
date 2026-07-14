"use client";
import { cn } from "@/lib/utils";

interface ScoreReadonlyProps {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  className?: string;
}

export function ScoreReadonly({ label, value, unit, className }: ScoreReadonlyProps) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-gray-400">{label}</span>
        <span className="text-[10px] bg-blue-50 text-blue-400 border border-blue-100 rounded px-1 py-px font-medium leading-none select-none">
          calculado
        </span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-sm font-semibold text-gray-700 tabular-nums">
          {value !== undefined && value !== null && value !== "" ? value : "—"}
        </span>
        {unit && <span className="text-xs text-gray-400">{unit}</span>}
      </div>
    </div>
  );
}
