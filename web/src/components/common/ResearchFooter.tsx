export function ResearchFooter() {
  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/35 pb-[calc(6rem+env(safe-area-inset-bottom))] sm:pb-0">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-1.5 px-4 py-5 text-center text-xs leading-relaxed text-[var(--color-text-muted)] sm:py-6">
        <p className="font-medium text-[var(--color-text)]">
          © 2026 PetirDashboard · Universitas Muhammadiyah Bangka Belitung
        </p>
        <p className="max-w-3xl">
          Dikembangkan sebagai luaran penelitian dosen dengan dukungan pendanaan dari{" "}
          <a
            href="https://kemdiktisaintek.go.id/"
            target="_blank"
            rel="noreferrer"
            className="font-medium text-blue-400 underline-offset-2 transition-colors hover:text-blue-300 hover:underline"
          >
            Kementerian Pendidikan Tinggi, Sains, dan Teknologi Republik Indonesia
          </a>
          .
        </p>
      </div>
    </footer>
  );
}
