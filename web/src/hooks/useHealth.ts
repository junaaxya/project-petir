"use client";

import { useQuery } from "@tanstack/react-query";
import { getHealthDiagnostics, getHealthLatest } from "@/lib/api";
import type { HealthDiagnosticsResponse, HealthLatestResponse } from "@/lib/types";

export function useHealth(node?: string) {
  return useQuery<HealthLatestResponse>({
    queryKey: ["health", "latest", node ?? null],
    queryFn: () => getHealthLatest(node),
    refetchInterval: 10_000,
    staleTime: 8_000,
  });
}

export function useHealthDiagnostics(node?: string, enabled = true) {
  return useQuery<HealthDiagnosticsResponse>({
    queryKey: ["health", "diagnostics", node ?? null],
    queryFn: () => getHealthDiagnostics(node),
    refetchInterval: 15_000,
    staleTime: 12_000,
    enabled,
  });
}
