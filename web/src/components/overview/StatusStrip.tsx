import { Badge } from "@/components/common/Badge";
import { StatusDot } from "@/components/common/StatusDot";
import { LightningStatusBadge } from "@/components/lightning/LightningStatusBadge";
import type { HealthLatestResponse, NodeStatus, HealthStream } from "@/lib/types";
import type { LightningLatestResponse } from "@/lib/api";
import type { LightningStatus } from "@contracts";
import { isRealtimeUnavailable, realtimeSnapshotDetail } from "@/lib/realtime";
import { nodeStatusLabel, streamStatusLabel } from "@/lib/uiLabels";

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
  const realtimeUnavailable = isRealtimeUnavailable(nodeStatus);
  const dotStatus = realtimeUnavailable ? "offline" : lightningToDotStatus(lightningStatus);
  const snapshotDetail = realtimeSnapshotDetail(nodeStatus, lightning?.minute?.minute_utc);

  const weatherStream = health?.streams?.find(
    (s) => s.table === "weather_minute_summary",
  );
  const weatherStreamStatus = weatherStream?.status ?? "no_data";

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-2 sm:gap-3 sm:px-4 sm:py-3">
      <div className="flex min-w-0 flex-col gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/50 px-2.5 py-2 sm:px-3.5">
        <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
          Lokasi sensor
        </span>
        <div className="flex min-w-0 flex-col gap-1.5">
          <div className="flex min-w-0 items-center gap-1.5">
            <StatusDot status={nodeStatus} pulse />
            <span className="truncate text-sm font-medium text-[var(--color-text)]">
              Kampus Unmuh Babel
            </span>
          </div>
          <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:flex-wrap sm:items-center sm:gap-1.5">
            {healthLoading ? (
              <div className="h-5 w-14 animate-pulse rounded-full bg-[var(--color-border)]" />
            ) : (
              <Badge variant={nodeStatus} label={nodeStatusLabel(nodeStatus)} />
            )}
            {health?.sync_lag_seconds != null && (
              <span className="truncate text-[11px] text-[var(--color-text-muted)]">
                {formatAge(health.sync_lag_seconds)}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:gap-3">
        <div className="flex min-w-0 flex-col gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/50 px-2.5 py-2 sm:px-3.5">
          <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
            Status cuaca
          </span>
          <div className="flex min-w-0 flex-col gap-1.5">
            <div className="flex min-w-0 items-center gap-1.5">
              <StatusDot status={weatherStreamStatus} />
              <span className="truncate text-sm font-medium text-[var(--color-text)]">Cuaca</span>
            </div>
            <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:flex-wrap sm:items-center sm:gap-1.5">
              {healthLoading ? (
                <div className="h-5 w-14 animate-pulse rounded-full bg-[var(--color-border)]" />
              ) : (
                <Badge variant={weatherStreamStatus} label={streamStatusLabel(weatherStreamStatus)} />
              )}
              {weatherStream?.last_ts_utc != null && (
                <span className="truncate text-[11px] text-[var(--color-text-muted)]">
                  {formatTimestampAge(weatherStream.last_ts_utc)}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/50 px-2.5 py-2 sm:px-3.5">
          <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
            Status petir
          </span>
          <div className="flex min-w-0 flex-col gap-1.5">
            <div className="flex min-w-0 items-center gap-1.5">
              <StatusDot status={dotStatus} />
              <span className="truncate text-sm font-medium text-[var(--color-text)]">Petir</span>
            </div>
            <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:flex-wrap sm:items-center sm:gap-1.5">
              {lightningLoading ? (
                <div className="h-5 w-14 animate-pulse rounded-full bg-[var(--color-border)]" />
              ) : realtimeUnavailable ? (
                <Badge variant="offline" label="Offline" />
              ) : (
                <LightningStatusBadge status={lightningStatus} />
              )}
              {realtimeUnavailable && snapshotDetail ? (
                <span className="line-clamp-2 text-[11px] text-[var(--color-text-muted)]">{snapshotDetail}</span>
              ) : lightning?.minute?.last_event_ts_utc != null ? (
                <span className="truncate text-[11px] text-[var(--color-text-muted)]">
                  {lightning.minute.last_distance_km != null
                    ? `${lightning.minute.last_distance_km} km · `
                    : ""}
                  {formatTimestampAge(lightning.minute.last_event_ts_utc)}
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
