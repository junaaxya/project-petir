"use client";

import { useState } from "react";
import { useHealth } from "@/hooks/useHealth";
import { useSystemEvents } from "@/hooks/useSystemEvents";
import { useIngestRuns } from "@/hooks/useIngestRuns";
import { NodeSelect } from "@/components/common/NodeSelect";
import { Badge } from "@/components/common/Badge";
import { FreshnessTable } from "@/components/health/FreshnessTable";
import { SystemEventsList } from "@/components/health/SystemEventsList";
import { BatchSuccessRate } from "@/components/health/BatchSuccessRate";
import { Card } from "@/components/common/Card";

function fmtLag(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h`;
}

export default function HealthPage() {
  const [node, setNode] = useState<string>("");

  const nodeParam = node || undefined;

  const { data: health, isLoading: healthLoading } = useHealth(nodeParam);
  const { data: sysEvents, isLoading: sysLoading } = useSystemEvents({
    node: nodeParam,
    limit: 50,
  });
  const { data: ingestRuns, isLoading: runsLoading } = useIngestRuns(nodeParam);

  const streams = health?.streams ?? [];
  const systemItems = sysEvents?.items ?? [];
  const runs = ingestRuns?.items ?? [];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Kesehatan</h1>
        <NodeSelect value={node} onChange={setNode} />
      </div>

      <Card className="flex flex-wrap items-center gap-6">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Status Node
          </p>
          {healthLoading ? (
            <div className="h-6 w-20 animate-pulse rounded-full bg-[var(--color-border)]" />
          ) : (
            <Badge
              variant={health?.node_status ?? "no_data"}
              label={health?.node_status ?? "no_data"}
            />
          )}
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Jeda Sinkronisasi
          </p>
          {healthLoading ? (
            <div className="h-6 w-16 animate-pulse rounded bg-[var(--color-border)]" />
          ) : (
            <span className="text-sm font-medium text-[var(--color-text)]">
              {fmtLag(health?.sync_lag_seconds ?? null)}
            </span>
          )}
        </div>
        {health?.node_id && (
          <div className="flex flex-col gap-1">
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
              ID Node
            </p>
            <span className="font-mono text-sm text-[var(--color-text)]">{health.node_id}</span>
          </div>
        )}
      </Card>

      <FreshnessTable streams={streams} loading={healthLoading} />

      <BatchSuccessRate runs={runs} loading={runsLoading} />

      <SystemEventsList items={systemItems} loading={sysLoading} />
    </div>
  );
}
