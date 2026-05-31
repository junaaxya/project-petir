import { Badge } from "@/components/common/Badge";
import { StatusDot } from "@/components/common/StatusDot";
import { LightningStatusBadge } from "@/components/lightning/LightningStatusBadge";
import type { HealthLatestResponse, NodeStatus } from "@/lib/types";
import type { LightningLatestResponse } from "@/lib/api";
import type { LightningStatus } from "@contracts";

function formatAge(seconds: number | null | undefined): string {
  if (seconds == null) return "tidak diketahui";
  if (seconds < 60) return `${seconds}d lalu`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m lalu`;
  return `${Math.floor(seconds / 3600)}j lalu`;
}

function formatTimestampAge(isoTs: string): string {
  const diffMs = Date.now() - new Date(isoTs).getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}d lalu`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m lalu`;
  return `${Math.floor(diffSec / 3600)}j lalu`;
}

type DotStatus = NodeStatus | "ok" | "warn" | "degraded" | "invalid";

function lightningToDotStatus(status: LightningStatus | null | undefined): DotStatus {
  if (!status || status === "no_data") return "no_data";
  if (status === "quiet") return "ok";
  if (status === "noise" || status === "disturber") return "warn";
  return "offline";
}

interface StatusStripProps {
  health: HealthLatestResponse | undefined;
  healthLoading: boolean;
  lightning: LightningLatestResponse | undefined;
  lightningLoading: boolean;
}

export function StatusStrip({ health, healthLoading, lightning, lightningLoading }: StatusStripProps) {
  const nodeStatus: NodeStatus = health?.node_status ?? "no_data";
  const lightningStatus = lightning?.minute?.status ?? null;
  const dotStatus = lightningToDotStatus(lightningStatus);

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
      <div className="flex items-center gap-2">
        <StatusDot status={nodeStatus} pulse />
        <span className="text-sm font-medium text-[var(--color-text)]">
          {health?.node_id ?? "Node"}
        </span>
        {healthLoading ? (
          <div className="h-5 w-14 animate-pulse rounded-full bg-[var(--color-border)]" />
        ) : (
          <Badge variant={nodeStatus} label={nodeStatus.replace("_", " ")} />
        )}
        {health?.sync_lag_seconds != null && (
          <span className="text-xs text-[var(--color-text-muted)]">
            {formatAge(health.sync_lag_seconds)}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <StatusDot status={dotStatus} />
        <span className="text-sm font-medium text-[var(--color-text)]">Petir</span>
        {lightningLoading ? (
          <div className="h-5 w-14 animate-pulse rounded-full bg-[var(--color-border)]" />
        ) : (
          <LightningStatusBadge status={lightningStatus} />
        )}
        {lightning?.minute?.last_event_ts_utc != null && (
          <span className="text-xs text-[var(--color-text-muted)]">
            {lightning.minute.last_distance_km != null
              ? `${lightning.minute.last_distance_km} km · `
              : ""}
            {formatTimestampAge(lightning.minute.last_event_ts_utc)}
          </span>
        )}
      </div>
    </div>
  );
}
