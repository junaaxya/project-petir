import type { NodeStatus } from "./types";

export function isRealtimeUnavailable(nodeStatus: NodeStatus | null | undefined): boolean {
  return nodeStatus === "offline";
}

export function formatRelativeFromIso(isoTs: string | null | undefined): string {
  if (!isoTs) return "waktu tidak diketahui";
  const diffMs = Date.now() - new Date(isoTs).getTime();
  const diffSec = Math.max(0, Math.floor(diffMs / 1000));
  if (diffSec < 60) return `${diffSec} detik lalu`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} menit lalu`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} jam lalu`;
  return `${Math.floor(diffSec / 86400)} hari lalu`;
}

export function realtimeSnapshotDetail(
  nodeStatus: NodeStatus | null | undefined,
  isoTs: string | null | undefined,
): string | undefined {
  if (nodeStatus !== "offline") return undefined;
  return `Data terakhir ${formatRelativeFromIso(isoTs)}`;
}
