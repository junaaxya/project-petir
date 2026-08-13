const COMPASS_16 = [
  "Utara",
  "Utara Timur Laut",
  "Timur Laut",
  "Timur Timur Laut",
  "Timur",
  "Timur Tenggara",
  "Tenggara",
  "Selatan Tenggara",
  "Selatan",
  "Selatan Barat Daya",
  "Barat Daya",
  "Barat Barat Daya",
  "Barat",
  "Barat Barat Laut",
  "Barat Laut",
  "Utara Barat Laut",
] as const;

const COMPASS_SHORT_16 = [
  "N",
  "NNE",
  "NE",
  "ENE",
  "E",
  "ESE",
  "SE",
  "SSE",
  "S",
  "SSW",
  "SW",
  "WSW",
  "W",
  "WNW",
  "NW",
  "NNW",
] as const;

function normalizeDegrees(deg: number): number {
  return ((deg % 360) + 360) % 360;
}

function compassIndex16(deg: number): number {
  return Math.round(normalizeDegrees(deg) / 22.5) % 16;
}

export function windCompassShort(deg: number): string {
  return COMPASS_SHORT_16[compassIndex16(deg)];
}

export function windCompassLabel(deg: number): string {
  return COMPASS_16[compassIndex16(deg)];
}

export function formatWindDirection(deg: number | null | undefined): string {
  if (deg == null) return "—";
  const normalized = normalizeDegrees(deg);
  return `${windCompassLabel(normalized)} (${normalized.toFixed(0)}°)`;
}
