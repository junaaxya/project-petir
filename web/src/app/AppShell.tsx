"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { BottomNav } from "@/components/common/BottomNav";
import { InstitutionLogos } from "@/components/common/InstitutionLogos";
import { ResearchFooter } from "@/components/common/ResearchFooter";

const NAV_LINKS = [
  { href: "/", label: "Ringkasan" },
  { href: "/weather", label: "Cuaca" },
  { href: "/lightning", label: "Petir" },
  { href: "/health", label: "Kesehatan" },
  { href: "/quality", label: "Kualitas" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPetirLabs = pathname === "/petirlabs";

  if (isPetirLabs) {
    return <main>{children}</main>;
  }

  return (
    <>
      <header className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[var(--color-bg)]/90 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4">
          <div className="flex min-h-14 items-center gap-2 py-2 sm:gap-4">
            <Link href="/" className="shrink-0 font-semibold tracking-tight text-[var(--color-text)]" aria-label="PetirDashboard — Ringkasan">
              ⚡ Petir
            </Link>
            <nav className="hidden items-center gap-1 lg:flex" aria-label="Navigasi utama">
              {NAV_LINKS.map((link) => <Link key={link.href} href={link.href} className="rounded-md px-3 py-1.5 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-text)]">{link.label}</Link>)}
            </nav>
            <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3"><InstitutionLogos /></div>
          </div>
          <nav className="hidden items-center justify-center gap-1 border-t border-[var(--color-border)] py-1.5 sm:flex lg:hidden" aria-label="Navigasi utama">
            {NAV_LINKS.map((link) => <Link key={link.href} href={link.href} className="rounded-md px-3 py-1.5 text-xs text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-text)] md:text-sm">{link.label}</Link>)}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl overflow-x-clip px-4 py-4 pb-20 sm:py-6 sm:pb-6">{children}</main>
      <ResearchFooter />
      <BottomNav />
    </>
  );
}
