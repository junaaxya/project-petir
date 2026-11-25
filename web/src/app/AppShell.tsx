"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { BottomNav } from "@/components/common/BottomNav";
import { InstitutionLogos } from "@/components/common/InstitutionLogos";
import { ResearchFooter } from "@/components/common/ResearchFooter";
import type { SiteConfig } from "@/lib/siteConfig";

const NAV_LINKS = [
  { href: "/", label: "Ringkasan" },
  { href: "/weather", label: "Cuaca" },
  { href: "/lightning", label: "Petir" },
  { href: "/health", label: "Kesehatan" },
  { href: "/quality", label: "Kualitas" },
];

export function AppShell({ children, site }: { children: ReactNode; site: SiteConfig }) {
  const pathname = usePathname();
  const isPetirLabs = pathname === "/petirlabs";
  const showSiteIdentity = site.siteId !== "petir-dashboard" || Boolean(site.stationVersion);

  if (isPetirLabs) {
    return <main>{children}</main>;
  }

  return (
    <>
      <header className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[var(--color-bg)]/90 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4">
          <div className="flex min-h-14 items-center gap-2 py-2 sm:gap-4">
            <div className="flex min-w-0 shrink items-center gap-2 sm:gap-3">
              <Link href="/" className="shrink-0 font-semibold tracking-tight text-[var(--color-text)]" aria-label={`${site.siteName} — Ringkasan`}>
                ⚡ Petir
              </Link>
              {showSiteIdentity ? (
                <div className="hidden min-w-0 border-l border-[var(--color-border)] pl-3 leading-tight sm:block" data-site-identity>
                  <p className="truncate text-sm font-medium text-[var(--color-text)]">{site.siteName}</p>
                  {site.stationVersion ? (
                    <p className="truncate text-xs text-[var(--color-text-muted)]">Stasiun {site.stationVersion}</p>
                  ) : null}
                </div>
              ) : null}
            </div>
            <nav className="hidden items-center gap-1 lg:flex" aria-label="Navigasi utama">
              {NAV_LINKS.map((link) => <Link key={link.href} href={link.href} className="rounded-md px-3 py-1.5 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-text)]">{link.label}</Link>)}
            </nav>
            <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3"><InstitutionLogos /></div>
          </div>
          {showSiteIdentity ? (
            <div className="flex items-baseline gap-2 border-t border-[var(--color-border)] py-1.5 sm:hidden" data-site-identity-mobile>
              <span className="text-xs font-medium text-[var(--color-text)]">{site.siteName}</span>
              {site.stationVersion ? <span className="text-[10px] text-[var(--color-text-muted)]">Stasiun {site.stationVersion}</span> : null}
            </div>
          ) : null}
          <nav className="hidden items-center justify-center gap-1 border-t border-[var(--color-border)] py-1.5 sm:flex lg:hidden" aria-label="Navigasi utama">
            {NAV_LINKS.map((link) => <Link key={link.href} href={link.href} className="rounded-md px-3 py-1.5 text-xs text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-text)] md:text-sm">{link.label}</Link>)}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl overflow-x-clip px-4 py-4 pb-[calc(6rem+env(safe-area-inset-bottom))] sm:py-6 sm:pb-6">{children}</main>
      <ResearchFooter />
      <BottomNav />
    </>
  );
}
