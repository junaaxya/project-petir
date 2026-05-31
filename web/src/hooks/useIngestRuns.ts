"use client";

import { useQuery } from "@tanstack/react-query";
import { getIngestRuns } from "@/lib/api";
import type { IngestRunsResponse } from "@/lib/api";

export function useIngestRuns(node?: string) {
  return useQuery<IngestRunsResponse>({
    queryKey: ["ingest", "runs", node ?? null],
    queryFn: () => getIngestRuns(node),
    refetchInterval: 60_000,
    staleTime: 50_000,
  });
}
