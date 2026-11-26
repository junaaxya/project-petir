import { DEFAULT_RAIN_SEMANTICS, parseRainSemantics, type RainSemantics } from "./rainSemantics";

export const DEFAULT_SITE_CONFIG = {
  siteName: "PetirDashboard",
  stationVersion: "",
  siteId: "petir-dashboard",
  publicDomain: "",
  rainSemantics: DEFAULT_RAIN_SEMANTICS,
} as const;

export type SiteConfig = {
  siteName: string;
  stationVersion: string;
  siteId: string;
  publicDomain: string;
  rainSemantics: RainSemantics;
};

type SiteEnvironment = {
  [key: string]: string | undefined;
  PETIR_SITE_NAME?: string;
  PETIR_STATION_VERSION?: string;
  PETIR_SITE_ID?: string;
  PETIR_PUBLIC_DOMAIN?: string;
  PETIR_RAIN_SEMANTICS?: string;
};

function valueOrDefault(value: string | undefined, fallback: string): string {
  const normalized = value?.trim();
  return normalized || fallback;
}

function normalizePublicDomain(value: string | undefined): string {
  const normalized = value?.trim().toLowerCase() ?? "";
  if (!normalized) return "";

  // Deployment configuration accepts a hostname only, never a URL or path.
  if (!/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(normalized)) {
    return "";
  }
  return normalized;
}

export function getSiteConfig(env: SiteEnvironment = process.env): SiteConfig {
  return {
    siteName: valueOrDefault(env.PETIR_SITE_NAME, DEFAULT_SITE_CONFIG.siteName),
    stationVersion: valueOrDefault(env.PETIR_STATION_VERSION, DEFAULT_SITE_CONFIG.stationVersion),
    siteId: valueOrDefault(env.PETIR_SITE_ID, DEFAULT_SITE_CONFIG.siteId),
    publicDomain: normalizePublicDomain(env.PETIR_PUBLIC_DOMAIN),
    rainSemantics: parseRainSemantics(env.PETIR_RAIN_SEMANTICS),
  };
}

export function sitePageTitle(site: SiteConfig): string {
  return site.siteName === DEFAULT_SITE_CONFIG.siteName
    ? DEFAULT_SITE_CONFIG.siteName
    : `${site.siteName} | ${DEFAULT_SITE_CONFIG.siteName}`;
}
