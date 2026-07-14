import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const RISK_COLORS: Record<string, string> = {
  critical: "text-red-500",
  high: "text-orange-500",
  medium: "text-yellow-500",
  low: "text-blue-400",
  info: "text-gray-400",
};

export const RISK_BG_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 border-red-500/30 text-red-400",
  high: "bg-orange-500/10 border-orange-500/30 text-orange-400",
  medium: "bg-yellow-500/10 border-yellow-500/30 text-yellow-400",
  low: "bg-blue-500/10 border-blue-500/30 text-blue-400",
  info: "bg-gray-500/10 border-gray-500/30 text-gray-400",
};

export const STATUS_COLORS: Record<string, string> = {
  open: "bg-red-500/10 text-red-400",
  confirmed: "bg-orange-500/10 text-orange-400",
  under_treatment: "bg-yellow-500/10 text-yellow-400",
  resolved: "bg-green-500/10 text-green-400",
  accepted: "bg-gray-500/10 text-gray-400",
  false_positive: "bg-gray-500/10 text-gray-500",
  draft: "bg-blue-500/10 text-blue-400",
  closed: "bg-green-500/10 text-green-400",
};

export function formatScore(score: number): string {
  return score.toFixed(2);
}

export function riskLevelLabel(level: string): string {
  return level.charAt(0).toUpperCase() + level.slice(1);
}

export function truncate(str: string, len: number): string {
  return str.length > len ? str.slice(0, len) + "…" : str;
}
