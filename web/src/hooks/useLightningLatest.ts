"use client";

import { useQuery } from "@tanstack/react-query";
import { getLightningLatest } from "@/lib/api";
import type { LightningLatestResponse } from "@/lib/api";

export function useLightningLatest(node?: string) {
  return useQuery<LightningLatestResponse>({
    queryKey: ["lightning", "latest", node ?? null],
    queryFn: () => getLightningLatest(node),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}
