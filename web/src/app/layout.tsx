import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "./AppShell";
import { getSiteConfig, sitePageTitle } from "@/lib/siteConfig";

// Site identity is deployment configuration. Force request-time evaluation so a
// single standalone image can serve Petir 1 defaults or a named Petir 2 site.
export const dynamic = "force-dynamic";

export function generateMetadata(): Metadata {
  const site = getSiteConfig();
  const description = `Dashboard pemantauan cuaca dan petir — ${site.siteName}`;

  return {
    title: sitePageTitle(site),
    description,
    applicationName: "PetirDashboard",
    ...(site.publicDomain ? { metadataBase: new URL(`https://${site.publicDomain}`) } : {}),
    other: {
      "petir-site-id": site.siteId,
      ...(site.stationVersion ? { "petir-station-version": site.stationVersion } : {}),
    },
  };
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const site = getSiteConfig();

  return (
    <html lang="id">
      <body data-petir-site-id={site.siteId} data-petir-station-version={site.stationVersion || undefined}>
        <Providers>
          <AppShell site={site}>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
