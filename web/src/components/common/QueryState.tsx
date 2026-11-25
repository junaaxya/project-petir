"use client";

import { Card } from "@/components/common/Card";
import { apiFailureKind, type ApiFailureKind } from "@/lib/api";

const PRESENTATION: Record<ApiFailureKind, { title: string; detail: string }> = {
  authentication: {
    title: "Autentikasi diperlukan",
    detail: "Masuk melalui akses yang disediakan untuk melihat bagian ini.",
  },
  forbidden: {
    title: "Akses tidak diizinkan",
    detail: "Identitas Anda tidak memiliki peran yang diperlukan untuk bagian ini.",
  },
  unavailable: {
    title: "Layanan belum tersedia",
    detail: "Layanan atau konfigurasi akses sedang tidak tersedia. Coba lagi setelah konfigurasi dipulihkan.",
  },
  network: {
    title: "Gagal terhubung",
    detail: "Periksa koneksi Anda lalu coba memuat data kembali.",
  },
  unexpected: {
    title: "Data gagal dimuat",
    detail: "Terjadi kesalahan saat mengambil data. Coba lagi beberapa saat.",
  },
};

interface QueryErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  compact?: boolean;
  label?: string;
}

export function QueryErrorState({ error, onRetry, compact = false, label }: QueryErrorStateProps) {
  const kind = apiFailureKind(error);
  const text = PRESENTATION[kind];
  const canRetry = onRetry && kind !== "authentication" && kind !== "forbidden";
  const content = (
    <div
      className="rounded-lg border border-amber-700/70 bg-amber-950/40 p-4 text-sm"
      role="alert"
      data-testid={`query-error-${kind}`}
    >
      {label ? <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-400">{label}</p> : null}
      <p className="font-semibold text-amber-100">{text.title}</p>
      <p className="mt-1 text-amber-200/85">{text.detail}</p>
      {canRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-amber-600/70 px-3 py-1.5 font-medium text-amber-100 hover:bg-amber-900/50"
        >
          Coba lagi
        </button>
      ) : null}
    </div>
  );
  return compact ? content : <Card>{content}</Card>;
}

interface DataFreshnessNoticeProps {
  updatedAtUtc: string | null | undefined;
  isStale: boolean;
  isFetching?: boolean;
}

export function DataFreshnessNotice({ updatedAtUtc, isStale, isFetching = false }: DataFreshnessNoticeProps) {
  if (!updatedAtUtc) return null;
  const updatedAt = new Date(updatedAtUtc);
  if (Number.isNaN(updatedAt.getTime())) return null;
  const formatted = updatedAt.toLocaleString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  return (
    <div
      className={`rounded-md border px-3 py-2 text-xs ${
        isStale
          ? "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
          : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)]"
      }`}
      data-testid={isStale ? "stale-data-indicator" : "fresh-data-indicator"}
      aria-live="polite"
    >
      {isStale ? "Data tidak terkini" : "Data diperbarui"} pukul {formatted}
      {isFetching ? " · memperbarui…" : ""}
    </div>
  );
}
