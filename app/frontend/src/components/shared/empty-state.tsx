"use client";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 text-center", className)}>
      {Icon && <Icon size={36} className="mb-4 text-gray-200" />}
      <p className="text-sm font-medium text-gray-500">{title}</p>
      {description && <p className="text-xs text-gray-400 mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function LoadingRows({ rows = 5, colSpan = 99 }: { rows?: number; colSpan?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className="border-t border-gray-100 animate-pulse">
          <td colSpan={colSpan} className="p-4">
            <div className="h-4 bg-gray-100 rounded w-3/4" />
          </td>
        </tr>
      ))}
    </>
  );
}

export function ErrorState({ message, className }: { message?: string; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-12 text-center", className)}>
      <p className="text-sm text-red-500 font-medium">Error al cargar datos</p>
      {message && <p className="text-xs text-gray-400 mt-1">{message}</p>}
    </div>
  );
}
