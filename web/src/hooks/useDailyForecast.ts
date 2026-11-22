"use client";

import { useQuery } from "@tanstack/react-query";
import { getDailyForecast, type DailyForecastResponse } from "@/lib/api";

export function useDailyForecast(node?: string) {
  return useQuery<DailyForecastResponse>({
    queryKey: ["weather", "daily-forecast", node ?? null],
    queryFn: () => getDailyForecast(node),
    refetchInterval: 60_000,
    staleTime: 50_000,
  });
}
