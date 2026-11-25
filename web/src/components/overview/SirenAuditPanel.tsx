"use client";

import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/common/Card";
import { QueryErrorState } from "@/components/common/QueryState";
import {
  ApiRequestError,
  createSirenAuditRequest,
  type CreateSirenAuditResponse,
  type SirenAuditHistoryItem,
  type SirenAuditStatus,
} from "@/lib/api";
import { useSirenAuditHistory, useSirenAuditLatest, useSirenAuditOptions } from "@/hooks/useSirenAudit";

interface SirenAuditPanelProps {
  node?: string;
}

const STATUS_OPTIONS: Array<{ value: "" | SirenAuditStatus; label: string }> = [
  { value: "", label: "Semua status" },
  { value: "queued", label: "Queued" },
  { value: "dispatched", label: "Dispatched" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "executing", label: "Executing" },
  { value: "success", label: "Success" },
  { value: "failed", label: "Failed" },
  { value: "rejected", label: "Rejected" },
];

function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("id-ID", {
    timeZone: "Asia/Jakarta",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }) + " WIB";
}

function formatCountdown(seconds?: number | null): string {
  const value = Math.max(0, Number(seconds ?? 0));
  if (value <= 0) return "Siap dipakai";
  if (value < 60) return `${value} detik lagi`;
  const minutes = Math.floor(value / 60);
  const remain = value % 60;
  return remain > 0 ? `${minutes}m ${remain}d lagi` : `${minutes} menit lagi`;
}

function localInputValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function statusTone(status: SirenAuditStatus | null | undefined): string {
  switch (status) {
    case "success":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
    case "failed":
    case "rejected":
      return "border-red-500/30 bg-red-500/10 text-red-300";
    case "executing":
    case "acknowledged":
    case "dispatched":
      return "border-sky-500/30 bg-sky-500/10 text-sky-300";
    case "queued":
      return "border-amber-500/30 bg-amber-500/10 text-amber-300";
    default:
      return "border-slate-500/30 bg-slate-500/10 text-slate-300";
  }
}

function statusLabel(status: SirenAuditStatus | null | undefined): string {
  switch (status) {
    case "queued":
      return "Menunggu antrean";
    case "dispatched":
      return "Sudah dikirim ke node";
    case "acknowledged":
      return "Diterima node";
    case "executing":
      return "Sedang dijalankan";
    case "success":
      return "Berhasil";
    case "failed":
      return "Gagal";
    case "rejected":
      return "Ditolak";
    default:
      return "Belum ada status";
  }
}

function summarizeCommand(item?: CreateSirenAuditResponse | SirenAuditHistoryItem | null): string {
  if (!item) return "—";
  return `${item.durationSec} detik × ${item.repeats} kali, jeda ${item.gapSec} detik`;
}

export function SirenAuditPanel({ node }: SirenAuditPanelProps) {
  const queryClient = useQueryClient();
  const optionsQuery = useSirenAuditOptions();
  const { data: options, isLoading: optionsLoading } = optionsQuery;
  const [targetNode, setTargetNode] = useState(node ?? "");
  const [requestedBy, setRequestedBy] = useState("");
  const [durationSec, setDurationSec] = useState("2");
  const [repeats, setRepeats] = useState("1");
  const [gapSec, setGapSec] = useState("1");
  const [reason, setReason] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CreateSirenAuditResponse | null>(null);

  const initialFrom = useMemo(() => {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    return localInputValue(start);
  }, []);
  const initialTo = useMemo(() => localInputValue(new Date()), []);
  const [filterNode, setFilterNode] = useState(node ?? "");
  const [filterStatus, setFilterStatus] = useState<"" | SirenAuditStatus>("");
  const [filterFrom, setFilterFrom] = useState(initialFrom);
  const [filterTo, setFilterTo] = useState(initialTo);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (node) {
      setTargetNode(node);
      setFilterNode(node);
    }
  }, [node]);

  useEffect(() => {
    if (!options?.operators?.length) return;
    if (requestedBy) return;
    setRequestedBy(options.operators[0]?.id ?? "");
  }, [options?.operators, requestedBy]);

  useEffect(() => {
    if (!options?.nodes?.length) return;
    if (targetNode) return;
    const eligible = options.nodes.find((item) => item.eligible);
    setTargetNode(eligible?.nodeId ?? options.nodes[0]?.nodeId ?? "");
  }, [options?.nodes, targetNode]);

  const latestNode = targetNode || node || undefined;
  const latestQuery = useSirenAuditLatest(latestNode);
  const { data: latest, isLoading: latestLoading } = latestQuery;
  const historyQuery = useSirenAuditHistory({
    node: filterNode || undefined,
    status: filterStatus || undefined,
    from: filterFrom ? new Date(filterFrom).toISOString() : undefined,
    to: filterTo ? new Date(filterTo).toISOString() : undefined,
    page,
    page_size: 5,
  });
  const { data: history, isLoading: historyLoading } = historyQuery;

  const validations = useMemo(() => {
    const duration = Number(durationSec);
    const repeatsValue = Number(repeats);
    const gap = Number(gapSec);
    const errors: string[] = [];
    if (!targetNode) errors.push("Pilih node tujuan.");
    if (!requestedBy) errors.push("Pilih operator.");
    if (!Number.isFinite(duration) || duration < 0.5 || duration > 10) errors.push("Durasi harus 0.5–10 detik.");
    if (!Number.isInteger(repeatsValue) || repeatsValue < 1 || repeatsValue > 3) errors.push("Ulangan harus 1–3 kali.");
    if (!Number.isFinite(gap) || gap < 0 || gap > 10) errors.push("Jeda harus 0–10 detik.");
    if (!reason.trim()) errors.push("Alasan wajib diisi.");
    return errors;
  }, [durationSec, gapSec, reason, repeats, requestedBy, targetNode]);

  const latestItem = latest?.latest ?? null;
  const cooldownActive = (latestItem?.cooldownRemainingSeconds ?? 0) > 0 && latestItem?.nodeId === latestNode;
  const operatorsConfigured = (options?.operators?.length ?? 0) > 0;
  const nodesConfigured = (options?.nodes?.length ?? 0) > 0;
  const submitDisabled = submitting || validations.length > 0 || !operatorsConfigured || !nodesConfigured;

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await createSirenAuditRequest({
        nodeId: targetNode,
        requestedBy,
        durationSec: Number(durationSec),
        repeats: Number(repeats),
        gapSec: Number(gapSec),
        reason: reason.trim(),
      });
      setResult(response);
      setShowConfirm(false);
      setReason("");
      setRepeats("1");
      setGapSec("1");
      setDurationSec("2");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["siren-audit-latest"] }),
        queryClient.invalidateQueries({ queryKey: ["siren-audit-history"] }),
      ]);
    } catch (error) {
      if (error instanceof ApiRequestError) {
        const cooldownHint = typeof error.payload?.cooldownRemainingSeconds === "number"
          ? ` Cooldown aktif ${formatCountdown(error.payload.cooldownRemainingSeconds as number)}.`
          : "";
        setSubmitError(`${error.message}.${cooldownHint}`.trim());
      } else {
        setSubmitError("Gagal mengirim permintaan test sirine.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const failedQuery = [optionsQuery, latestQuery, historyQuery].find((query) => query.isError);
  if (failedQuery?.isError) {
    return (
      <QueryErrorState
        error={failedQuery.error}
        onRetry={() => failedQuery.refetch()}
        label="Audit sirine"
      />
    );
  }

  return (
    <Card className="space-y-4">
      <div className="space-y-1">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-[var(--color-text)] sm:text-lg">Audit / Test Sirine Manual</h2>
            <p className="text-sm text-[var(--color-text-muted)]">
              Server mencatat audit, memberi cooldown, dan membuat command ke node Raspberry Pi tanpa menyalakan GPIO di server lab.
            </p>
          </div>
          {latestItem ? (
            <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${statusTone(latestItem.status)}`}>
              Status terakhir: {statusLabel(latestItem.status)}
            </span>
          ) : null}
        </div>

        {!optionsLoading && !operatorsConfigured ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            Operator audit sirine belum dikonfigurasi di server. Isi env `SIREN_AUDIT_OPERATORS_JSON` dulu agar tombol kirim aktif.
          </div>
        ) : null}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
        <div className="space-y-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg)]/40 p-3 sm:p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm text-[var(--color-text-muted)]">
              <span className="font-medium text-[var(--color-text)]">Node tujuan</span>
              <select
                value={targetNode}
                onChange={(event) => setTargetNode(event.target.value)}
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
              >
                <option value="">Pilih node</option>
                {(options?.nodes ?? []).map((item) => (
                  <option key={item.nodeId} value={item.nodeId}>
                    {item.name || item.nodeId}{item.eligible ? "" : " • tidak siap"}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm text-[var(--color-text-muted)]">
              <span className="font-medium text-[var(--color-text)]">Operator</span>
              <select
                value={requestedBy}
                onChange={(event) => setRequestedBy(event.target.value)}
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
              >
                <option value="">Pilih operator</option>
                {(options?.operators ?? []).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name || item.id} • {item.role}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm text-[var(--color-text-muted)]">
              <span className="font-medium text-[var(--color-text)]">Durasi bunyi</span>
              <input
                value={durationSec}
                onChange={(event) => setDurationSec(event.target.value)}
                inputMode="decimal"
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
                placeholder="2"
              />
              <p className="text-xs">Batas {options?.limits.durationSec.min ?? 0.5}–{options?.limits.durationSec.max ?? 10} detik</p>
            </label>

            <label className="space-y-1 text-sm text-[var(--color-text-muted)]">
              <span className="font-medium text-[var(--color-text)]">Jumlah ulangan</span>
              <input
                value={repeats}
                onChange={(event) => setRepeats(event.target.value)}
                inputMode="numeric"
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
                placeholder="1"
              />
              <p className="text-xs">Batas {options?.limits.repeats.min ?? 1}–{options?.limits.repeats.max ?? 3} kali</p>
            </label>

            <label className="space-y-1 text-sm text-[var(--color-text-muted)] sm:col-span-2">
              <span className="font-medium text-[var(--color-text)]">Jeda antar bunyi</span>
              <input
                value={gapSec}
                onChange={(event) => setGapSec(event.target.value)}
                inputMode="decimal"
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
                placeholder="1"
              />
            </label>
          </div>

          <label className="space-y-1 text-sm text-[var(--color-text-muted)]">
            <span className="font-medium text-[var(--color-text)]">Alasan test</span>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              rows={3}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
              placeholder="Contoh: verifikasi relay sirine setelah maintenance"
            />
          </label>

          {validations.length > 0 ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              <ul className="list-disc space-y-1 pl-4">
                {validations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {submitError ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {submitError}
            </div>
          ) : null}

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-[var(--color-text-muted)]">
              Cooldown per node: {options?.limits.cooldownSeconds ?? 60} detik. Status dikunci supaya test tidak spam.
            </p>
            <button
              type="button"
              disabled={submitDisabled}
              onClick={() => setShowConfirm(true)}
              className="inline-flex items-center justify-center rounded-xl bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Mengirim..." : "Kirim test sirine"}
            </button>
          </div>
        </div>

        <div className="space-y-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg)]/40 p-3 sm:p-4">
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-[var(--color-text)]">Status terakhir</h3>
            {latestLoading ? (
              <p className="text-sm text-[var(--color-text-muted)]">Memuat status sirine...</p>
            ) : latestItem ? (
              <div className="space-y-3">
                <div className={`rounded-xl border px-3 py-2 text-sm ${statusTone(latestItem.status)}`}>
                  <div className="font-medium">{statusLabel(latestItem.status)}</div>
                  <div className="mt-1 text-xs opacity-90">Node {latestItem.nodeId} • {formatDateTime(latestItem.requestedAt)}</div>
                </div>
                <dl className="grid grid-cols-1 gap-2 text-sm text-[var(--color-text-muted)]">
                  <div>
                    <dt className="font-medium text-[var(--color-text)]">Operator</dt>
                    <dd>{latestItem.requestedBy} • {latestItem.requestedRole}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-[var(--color-text)]">Pola test</dt>
                    <dd>{summarizeCommand(latestItem)}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-[var(--color-text)]">Cooldown</dt>
                    <dd>{formatCountdown(latestItem.cooldownRemainingSeconds)}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-[var(--color-text)]">Alasan</dt>
                    <dd>{latestItem.reason}</dd>
                  </div>
                  {latestItem.resultMessage ? (
                    <div>
                      <dt className="font-medium text-[var(--color-text)]">Pesan hasil</dt>
                      <dd>{latestItem.resultMessage}</dd>
                    </div>
                  ) : null}
                </dl>
                {latest?.statusUpdates?.length ? (
                  <div className="space-y-2">
                    <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">Jejak status</p>
                    <div className="space-y-2">
                      {latest.statusUpdates.map((item) => (
                        <div key={`${item.status}-${item.reportedAt}`} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusTone(item.status)}`}>{statusLabel(item.status)}</span>
                            <span className="text-xs text-[var(--color-text-muted)]">{formatDateTime(item.reportedAt)}</span>
                          </div>
                          {item.message ? <p className="mt-1 text-[var(--color-text-muted)]">{item.message}</p> : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">Belum ada audit sirine yang tercatat.</p>
            )}
          </div>

          {result ? (
            <div className="space-y-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-3 text-sm text-emerald-100">
              <div className="font-medium">Permintaan terakhir berhasil dibuat</div>
              <div>ID request: <span className="font-mono text-xs">{result.requestId}</span></div>
              <div>Status awal: {statusLabel(result.status)}</div>
              <div>Command: {summarizeCommand(result)}</div>
            </div>
          ) : null}

          {cooldownActive ? (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
              Node ini masih cooldown: {formatCountdown(latestItem?.cooldownRemainingSeconds)}
            </div>
          ) : null}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="min-w-[180px] flex-1 space-y-1 text-sm text-[var(--color-text-muted)]">
            <span className="font-medium text-[var(--color-text)]">Filter node</span>
            <select
              value={filterNode}
              onChange={(event) => {
                setFilterNode(event.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
            >
              <option value="">Semua node</option>
              {(options?.nodes ?? []).map((item) => (
                <option key={item.nodeId} value={item.nodeId}>{item.name || item.nodeId}</option>
              ))}
            </select>
          </div>

          <div className="min-w-[160px] flex-1 space-y-1 text-sm text-[var(--color-text-muted)]">
            <span className="font-medium text-[var(--color-text)]">Filter status</span>
            <select
              value={filterStatus}
              onChange={(event) => {
                setFilterStatus(event.target.value as "" | SirenAuditStatus);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
            >
              {STATUS_OPTIONS.map((item) => (
                <option key={item.label} value={item.value}>{item.label}</option>
              ))}
            </select>
          </div>

          <label className="min-w-[180px] flex-1 space-y-1 text-sm text-[var(--color-text-muted)]">
            <span className="font-medium text-[var(--color-text)]">Dari</span>
            <input
              type="datetime-local"
              value={filterFrom}
              onChange={(event) => {
                setFilterFrom(event.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
            />
          </label>

          <label className="min-w-[180px] flex-1 space-y-1 text-sm text-[var(--color-text-muted)]">
            <span className="font-medium text-[var(--color-text)]">Sampai</span>
            <input
              type="datetime-local"
              value={filterTo}
              onChange={(event) => {
                setFilterTo(event.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] outline-none"
            />
          </label>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-[var(--color-text)]">Riwayat test sirine</h3>
            <span className="text-xs text-[var(--color-text-muted)]">
              {history?.meta.total_items ?? 0} data
            </span>
          </div>

          {historyLoading || optionsLoading ? (
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/40 px-3 py-4 text-sm text-[var(--color-text-muted)]">
              Memuat riwayat sirine...
            </div>
          ) : history?.items?.length ? (
            <div className="space-y-2">
              {history.items.map((item) => (
                <div key={item.requestId} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/40 px-3 py-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusTone(item.status)}`}>
                          {statusLabel(item.status)}
                        </span>
                        <span className="text-xs text-[var(--color-text-muted)]">{formatDateTime(item.requestedAt)}</span>
                      </div>
                      <p className="text-sm font-medium text-[var(--color-text)]">{item.nodeId} • {item.requestedBy}</p>
                      <p className="text-sm text-[var(--color-text-muted)]">{item.reason}</p>
                    </div>
                    <div className="text-xs text-[var(--color-text-muted)] sm:text-right">
                      <div>{summarizeCommand(item)}</div>
                      <div>Cooldown: {formatCountdown(item.cooldownRemainingSeconds)}</div>
                    </div>
                  </div>
                </div>
              ))}

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-[var(--color-text-muted)]">
                  Halaman {history.meta.page} dari {history.meta.total_pages}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={!history.meta.has_prev}
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                    className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Sebelumnya
                  </button>
                  <button
                    type="button"
                    disabled={!history.meta.has_next}
                    onClick={() => setPage((current) => current + 1)}
                    className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Berikutnya
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/40 px-3 py-4 text-sm text-[var(--color-text-muted)]">
              Belum ada riwayat yang cocok dengan filter.
            </div>
          )}
        </div>
      </div>

      {showConfirm ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/70 p-3 sm:items-center">
          <div className="w-full max-w-lg rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-2xl">
            <div className="space-y-2">
              <h3 className="text-base font-semibold text-[var(--color-text)]">Konfirmasi test sirine</h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                Pastikan node, durasi, dan alasan sudah benar. Request ini akan dicatat ke audit log server dan membuat command ke edge node.
              </p>
              <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/40 p-3 text-sm text-[var(--color-text-muted)]">
                <div><span className="font-medium text-[var(--color-text)]">Node:</span> {targetNode || "—"}</div>
                <div><span className="font-medium text-[var(--color-text)]">Operator:</span> {requestedBy || "—"}</div>
                <div><span className="font-medium text-[var(--color-text)]">Pola:</span> {durationSec} detik × {repeats} kali, jeda {gapSec} detik</div>
                <div><span className="font-medium text-[var(--color-text)]">Alasan:</span> {reason || "—"}</div>
              </div>
            </div>
            <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => setShowConfirm(false)}
                className="rounded-xl border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-text)]"
              >
                Batal
              </button>
              <button
                type="button"
                disabled={submitDisabled}
                onClick={handleSubmit}
                className="rounded-xl bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Mengirim..." : "Ya, kirim test sirine"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </Card>
  );
}
