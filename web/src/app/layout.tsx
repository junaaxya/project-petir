import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Providers } from "./providers";
import Link from "next/link";

export const metadata: Metadata = {
  title: "PetirDashboard",
  description: "Dashboard pemantauan cuaca dan petir",
};

const NAV_LINKS = [
  { href: "/", label: "Ringkasan" },
  { href: "/weather", label: "Cuaca" },
  { href: "/lightning", label: "Petir" },
  { href: "/health", label: "Kesehatan" },
  { href: "/quality", label: "Kualitas" },
];

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="id">
      <body>
        <Providers>
          <header className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[var(--color-bg)]/90 backdrop-blur">
            <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
              <span className="font-semibold tracking-tight text-[var(--color-text)]">
                ⚡ Petir
              </span>
              <nav className="flex items-center gap-1">
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="rounded-md px-3 py-1.5 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-text)]"
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
