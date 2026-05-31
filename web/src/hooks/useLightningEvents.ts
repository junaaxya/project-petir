"use client";

import { useQuery } from "@tanstack/react-query";
import { getLightningEvents } from "@/lib/api";
import type { LightningEventsParams, LightningEventsResponse } from "@/lib/api";

export function useLightningEvents(params: LightningEventsParams) {
  return useQuery<LightningEventsResponse>({
    queryKey: ["lightning", "events", params],
    queryFn: () => getLightningEvents(params),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}
