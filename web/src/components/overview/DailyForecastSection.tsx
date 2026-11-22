"use client";

import { Card } from "@/components/common/Card";
import { useDailyForecast } from "@/hooks/useDailyForecast";
import type { DailyForecastItem, DailyForecastLevel } from "@/lib/api";

function levelStyles(level: DailyForecastLevel) {
  if (level === "tinggi") {
    return { badge: "border-red-500/30 bg-red-500/10 text-red-300", dot: "bg-red-400" };
  }
  if (level === "sedang") {
    return { badge: "border-amber-500/30 bg-amber-500/10 text-amber-300", dot: "bg-amber-400" };
  }
  return { badge: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300", dot: "bg-emerald-400" };
}

function levelLabel(level: DailyForecastLevel) {
  return level === "tinggi" ? "Tinggi" : level === "sedang" ? "Sedang" : "Rendah";
}

function ForecastCard({ item }: { item: DailyForecastItem }) {
  const styles = levelStyles(item.level);
  const baseTimeLabel = item.kind === "petir"
    ? "Perkiraan waktu petir"
    : item.kind === "hujan"
      ? "Perkiraan waktu hujan"
      : "Perkiraan waktu angin kencang";

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">{item.label}</p>
          <div className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${styles.badge}`}>
            <span className={`inline-flex h-2 w-2 rounded-full ${styles.dot}`} aria-hidden="true" />
            {levelLabel(item.level)}
          </div>
        </div>
        <div className="text-right">
          <p className="text-[11px] text-[var(--color-text-muted)]">{baseTimeLabel}</p>
          <p className="text-sm font-semibold text-[var(--color-text)]">
            {item.peak_window ? `${item.peak_window} WIB` : "Belum ada waktu dominan"}
          </p>
        </div>
      </div>
      <p className="text-sm text-[var(--color-text-muted)]">{item.reasons.join(" • ")}</p>
    </Card>
  );
}

export function DailyForecastSection({ node }: { node?: string }) {
  const query = useDailyForecast(node);

  return (
    <section className="flex flex-col gap-3">
      <div className="space-y-1">
        <h2 className="text-base font-semibold text-[var(--color-text)] sm:text-lg">Prediksi Hari Ini</h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          {query.data ? `Hari ini ${query.data.today_label} (WIB)` : "Hari ini (WIB)"}
        </p>
      </div>

      {query.isLoading ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, idx) => (
            <div key={idx} className="h-36 animate-pulse rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]" />
          ))}
        </div>
      ) : query.isError ? (
        <Card className="text-sm text-[var(--color-text-muted)]">
          Prediksi hari ini belum dapat dimuat. Data cuaca saat ini tetap dapat dipantau di bawah.
        </Card>
      ) : query.data?.status !== "available" ? (
        <Card className="text-sm text-[var(--color-text-muted)]">
          {query.data?.status === "stale_data"
            ? "Prediksi belum tersedia karena data sensor terbaru sudah tidak cukup segar."
            : "Prediksi belum tersedia karena data hari ini belum mencukupi."}
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {(query.data?.items ?? []).map((item) => (
            <ForecastCard key={item.kind} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}
