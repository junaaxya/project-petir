"use client";

interface PaginationControlsProps {
  page: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function PaginationControls({
  page,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
}: PaginationControlsProps) {
  const safeTotalPages = Math.max(1, totalPages);
  const currentPage = Math.min(Math.max(1, page), safeTotalPages);
  const start = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const end = totalItems === 0 ? 0 : Math.min(totalItems, currentPage * pageSize);

  return (
    <div className="mt-3 flex flex-col gap-2 text-xs text-[var(--color-text-muted)] sm:flex-row sm:items-center sm:justify-between">
      <span>
        Menampilkan {start}-{end} dari {totalItems} data
      </span>
      <div className="flex items-center justify-between gap-2 sm:justify-end">
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="rounded-md border border-[var(--color-border)] px-3 py-1 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Sebelumnya
        </button>
        <span>
          Halaman {currentPage} / {safeTotalPages}
        </span>
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= safeTotalPages}
          className="rounded-md border border-[var(--color-border)] px-3 py-1 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Berikutnya
        </button>
      </div>
    </div>
  );
}
