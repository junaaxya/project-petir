import { useQuery } from "@tanstack/react-query";
import {
  getSirenAuditHistory,
  getSirenAuditLatest,
  getSirenAuditOptions,
  type SirenAuditHistoryParams,
} from "@/lib/api";

export function useSirenAuditOptions() {
  return useQuery({
    queryKey: ["siren-audit-options"],
    queryFn: () => getSirenAuditOptions(),
    staleTime: 60_000,
  });
}

export function useSirenAuditLatest(node?: string) {
  return useQuery({
    queryKey: ["siren-audit-latest", node ?? "all"],
    queryFn: () => getSirenAuditLatest(node),
    refetchInterval: 15_000,
  });
}

export function useSirenAuditHistory(params: SirenAuditHistoryParams) {
  return useQuery({
    queryKey: ["siren-audit-history", params],
    queryFn: () => getSirenAuditHistory(params),
    placeholderData: (previous) => previous,
  });
}
