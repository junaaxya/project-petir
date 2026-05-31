"use client";

import { useQuery } from "@tanstack/react-query";
import { getLightningHistory } from "@/lib/api";
import type { LightningHistoryParams } from "@/lib/api";
import type { HistoryResponse } from "@/lib/types";

export function useLightningHistory(params: LightningHistoryParams) {
  return useQuery<HistoryResponse>({
    queryKey: ["lightning", "history", params],
    queryFn: () => getLightningHistory(params),
    refetchInterval: 60_000,
    staleTime: 50_000,
  });
}
