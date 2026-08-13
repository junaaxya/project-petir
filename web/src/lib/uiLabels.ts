import type { LightningStatus, QualityStatus } from "@contracts";
import type { HealthStream, NodeStatus } from "@/lib/types";

export function nodeStatusLabel(status: NodeStatus | null | undefined): string {
  const value = status ?? "no_data";
  const labels: Record<NodeStatus, string> = {
    fresh: "Aktif",
    stale: "Terlambat",
    offline: "Offline",
    no_data: "Belum ada data",
  };
  return labels[value];
}

export function streamStatusLabel(status: HealthStream["status"]): string {
  const labels: Record<HealthStream["status"], string> = {
    fresh: "Aktif",
    stale: "Terlambat",
    offline: "Offline",
    no_data: "Belum ada data",
    idle: "Siaga",
    unknown: "Tidak diketahui",
  };
  return labels[status];
}

export function lightningStatusLabel(status: LightningStatus | null | undefined): string {
  const value = status ?? "no_data";
  const labels: Record<LightningStatus, string> = {
    quiet: "Tenang",
    noise: "Derau tinggi",
    disturber: "Gangguan",
    activity: "Ada petir",
    saturated: "Sangat aktif",
    no_data: "Belum ada data",
  };
  return labels[value];
}

export function qualityStatusLabel(status: QualityStatus | null | undefined): string {
  const value = status ?? null;
  if (!value) return "—";
  const labels: Record<QualityStatus, string> = {
    ok: "Baik",
    warn: "Perlu perhatian",
    invalid: "Tidak valid",
  };
  return labels[value];
}
