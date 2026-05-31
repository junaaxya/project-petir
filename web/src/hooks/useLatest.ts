"use client";

import { useQuery } from "@tanstack/react-query";
import { getWeatherLatest } from "@/lib/api";
import type { WeatherLatestResponse } from "@/lib/types";

export function useWeatherLatest(node?: string) {
  return useQuery<WeatherLatestResponse>({
    queryKey: ["weather", "latest", node ?? null],
    queryFn: () => getWeatherLatest(node),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}
