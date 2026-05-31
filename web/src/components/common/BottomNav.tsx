"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/", label: "Ringkasan", icon: "⊞" },
  { href: "/weather", label: "Cuaca", icon: "🌤" },
  { href: "/lightning", label: "Petir", icon: "⚡" },
  { href: "/health", label: "Kesehatan", icon: "♥" },
  { href: "/quality", label: "Kualitas", icon: "◈" },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-20 border-t border-[var(--color-border)] bg-[var(--color-bg)]/95 backdrop-blur sm:hidden">
      <div className="flex items-stretch">
        {NAV_LINKS.map((link) => {
          const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-center transition-colors min-h-[56px] ${
                active
                  ? "text-blue-400"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              <span className="text-base leading-none" aria-hidden="true">
                {link.icon}
              </span>
              <span className="text-[10px] font-medium leading-tight">{link.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
