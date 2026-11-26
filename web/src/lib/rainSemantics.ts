export type RainSemantics = "legacy" | "rolling_1m_max";

export const DEFAULT_RAIN_SEMANTICS: RainSemantics = "legacy";

export function parseRainSemantics(value: string | undefined): RainSemantics {
  return value?.trim() === "rolling_1m_max" ? "rolling_1m_max" : DEFAULT_RAIN_SEMANTICS;
}

export function rainOverviewLabel(semantics: RainSemantics): string {
  return semantics === "rolling_1m_max" ? "Maks. Hujan Rolling 1 Menit" : "Hujan";
}

export function rainChartSubtitle(semantics: RainSemantics, raw: boolean): string {
  if (semantics !== "rolling_1m_max") return "Akumulasi hujan (mm)";
  return raw ? "Hujan rolling 1 menit (mm)" : "Maksimum hujan rolling 1 menit per interval (mm)";
}

export function rainSeriesLabel(semantics: RainSemantics, raw: boolean): string {
  if (semantics !== "rolling_1m_max") return "Hujan (mm)";
  return raw ? "Hujan Rolling 1 Menit (mm)" : "Maks Hujan Rolling 1 Menit (mm)";
}
