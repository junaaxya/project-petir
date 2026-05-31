import type { NodeStatus, StreamStatus, WeatherStatus } from "@/lib/types";

type StatusVariant = NodeStatus | StreamStatus | WeatherStatus | "lightning_nodata";

const variantStyles: Record<string, string> = {
  fresh: "bg-green-900/40 text-green-400 border-green-800",
  ok: "bg-green-900/40 text-green-400 border-green-800",
  stale: "bg-amber-900/40 text-amber-400 border-amber-800",
  warn: "bg-amber-900/40 text-amber-400 border-amber-800",
  degraded: "bg-amber-900/40 text-amber-400 border-amber-800",
  offline: "bg-red-900/40 text-red-400 border-red-800",
  invalid: "bg-red-900/40 text-red-400 border-red-800",
  idle: "bg-slate-900/50 text-slate-300 border-slate-700",
  unknown: "bg-gray-800/60 text-gray-400 border-gray-700",
  no_data: "bg-gray-800/60 text-gray-400 border-gray-700",
  lightning_nodata: "bg-gray-800/60 text-gray-400 border-gray-700",
};

interface BadgeProps {
  variant: StatusVariant;
  label: string;
}

export function Badge({ variant, label }: BadgeProps) {
  const styles = variantStyles[variant] ?? variantStyles["no_data"];
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles}`}
    >
      {label}
    </span>
  );
}
