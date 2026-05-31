"use client";

import type { LightningStatus } from "@contracts";
import { Badge } from "@/components/common/Badge";

const STATUS_LABELS: Record<LightningStatus, string> = {
  quiet: "Tenang",
  noise: "Derau",
  disturber: "Gangguan",
  activity: "Aktivitas",
  saturated: "Jenuh",
  no_data: "Tidak Ada Data",
};

const STATUS_VARIANTS: Record<LightningStatus, string> = {
  quiet: "ok",
  noise: "warn",
  disturber: "warn",
  activity: "offline",
  saturated: "offline",
  no_data: "no_data",
};

interface LightningStatusBadgeProps {
  status: LightningStatus | null;
  large?: boolean;
}

export function LightningStatusBadge({ status, large = false }: LightningStatusBadgeProps) {
  const s = status ?? "no_data";
  const label = STATUS_LABELS[s];
  const variant = STATUS_VARIANTS[s];

  if (large) {
    const colorMap: Record<string, string> = {
      ok: "bg-green-900/40 text-green-400 border-green-800",
      warn: "bg-amber-900/40 text-amber-400 border-amber-800",
      offline: "bg-red-900/40 text-red-400 border-red-800",
      no_data: "bg-gray-800/60 text-gray-400 border-gray-700",
    };
    const styles = colorMap[variant] ?? colorMap["no_data"];
    return (
      <span
        className={`inline-flex items-center rounded-2xl border px-5 py-2 text-base font-semibold tracking-wide ${styles}`}
      >
        {label}
      </span>
    );
  }

  return <Badge variant={variant as Parameters<typeof Badge>[0]["variant"]} label={label} />;
}
