"use client";

import { useQuery } from "@tanstack/react-query";
import { getQualityEvents } from "@/lib/api";
import type { QualityEventsParams, QualityEventsResponse } from "@/lib/api";

export function useQualityEvents(params: QualityEventsParams) {
  return useQuery<QualityEventsResponse>({
    queryKey: ["quality", "events", params],
    queryFn: () => getQualityEvents(params),
    refetchInterval: 60_000,
    staleTime: 50_000,
  });
}
