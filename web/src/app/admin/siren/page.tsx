"use client";

import { useState } from "react";
import { NodeSelect } from "@/components/common/NodeSelect";
import { SirenAuditPanel } from "@/components/overview/SirenAuditPanel";

export default function AdminSirenPage() {
  const [node, setNode] = useState<string>("");
  const nodeParam = node || undefined;

  return (
    <div className="flex flex-col gap-5 sm:gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:gap-3">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold text-[var(--color-text)] sm:text-2xl">Admin Sirine</h1>
          <p className="max-w-2xl text-sm text-[var(--color-text-muted)]">
            Halaman admin untuk audit dan test sirine manual. Tidak ditampilkan di halaman Ringkasan publik.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:items-end">
          <NodeSelect value={node} onChange={setNode} />
        </div>
      </div>

      <SirenAuditPanel node={nodeParam} />
    </div>
  );
}
