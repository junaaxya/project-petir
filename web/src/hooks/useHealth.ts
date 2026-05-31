"use client";

import { useQuery } from "@tanstack/react-query";
import { getHealthLatest } from "@/lib/api";
import type { HealthLatestResponse } from "@/lib/types";

export function useHealth(node?: string) {
  return useQuery<HealthLatestResponse>({
    queryKey: ["health", "latest", node ?? null],
    queryFn: () => getHealthLatest(node),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}
