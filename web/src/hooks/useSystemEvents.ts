"use client";

import { useQuery } from "@tanstack/react-query";
import { getSystemEvents } from "@/lib/api";
import type { SystemEventsParams, SystemEventsResponse } from "@/lib/api";

export function useSystemEvents(params: SystemEventsParams) {
  return useQuery<SystemEventsResponse>({
    queryKey: ["system", "events", params],
    queryFn: () => getSystemEvents(params),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}
