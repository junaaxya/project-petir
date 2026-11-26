"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { SiteConfig } from "@/lib/siteConfig";

const SiteConfigContext = createContext<SiteConfig | null>(null);

export function SiteConfigProvider({ site, children }: { site: SiteConfig; children: ReactNode }) {
  return <SiteConfigContext.Provider value={site}>{children}</SiteConfigContext.Provider>;
}

export function useSiteConfig(): SiteConfig {
  const site = useContext(SiteConfigContext);
  if (site == null) throw new Error("SiteConfigProvider is missing");
  return site;
}
