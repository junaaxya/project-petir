"use client";

import { useQuery } from "@tanstack/react-query";
import { getSystemEvents } from "@/lib/api";
import type { SystemEventsParams, SystemEventsResponse } from "@/lib/api";

export function useSystemEvents(params: SystemEventsParams, enabled = true) {
  return useQuery<SystemEventsResponse>({
    queryKey: ["system", "events", params],
    queryFn: () => getSystemEvents(params),
    refetchInterval: 10_000,
    staleTime: 8_000,
    enabled,
  });
}
