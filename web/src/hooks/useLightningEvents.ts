"use client";

import { useQuery } from "@tanstack/react-query";
import { getLatestLightningEvents, getLightningEvents } from "@/lib/api";
import type { LightningEventsParams, LightningEventsResponse } from "@/lib/api";

export function useLightningEvents(params: LightningEventsParams) {
  return useQuery<LightningEventsResponse>({
    queryKey: ["lightning", "events", params],
    queryFn: () => getLightningEvents(params),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}

export function useLatestLightningEvents(node?: string) {
  return useQuery<LightningEventsResponse>({
    queryKey: ["lightning", "events", "latest", node],
    queryFn: () => getLatestLightningEvents({ node, page_size: 20 }),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}
