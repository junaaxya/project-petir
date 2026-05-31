"use client";

import { useQuery } from "@tanstack/react-query";
import { getWeatherHistory } from "@/lib/api";
import type { WeatherHistoryParams } from "@/lib/api";
import type { HistoryResponse } from "@/lib/types";

export function useWeatherHistory(params: WeatherHistoryParams) {
  return useQuery<HistoryResponse>({
    queryKey: ["weather", "history", params],
    queryFn: () => getWeatherHistory(params),
    refetchInterval: 60_000,
    staleTime: 50_000,
  });
}
