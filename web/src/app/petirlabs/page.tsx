import Image from "next/image";
import Link from "next/link";

const steps = [
  {
    number: "01",
    title: "Sensor lokal",
    body: "Mengumpulkan cuaca dan aktivitas atmosfer dari perangkat sensor yang ditempatkan di lokasi pemantauan.",
  },
  {
    number: "02",
    title: "Data terstruktur",
    body: "Data disimpan sebagai riwayat waktu agar perubahan kondisi dan kualitas data dapat ditinjau kembali.",
  },
  {
    number: "03",
    title: "Keputusan lebih cepat",
    body: "Dashboard membantu operator membaca kondisi terbaru, aktivitas petir, dan kesehatan perangkat dalam satu tempat.",
  },
];

const audiences = ["Kampus dan sekolah", "Lokasi kerja berisiko", "Komunitas dan fasilitas publik"];

export default function PetirLabsLandingPage() {
  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/petirlabs" className="flex items-center gap-2 text-lg font-semibold tracking-tight text-[var(--color-text)]" aria-label="PetirLabs home">
          <span className="text-2xl text-emerald-300" aria-hidden="true">⚡</span>
          PetirLabs
        </Link>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link href="/" className="hidden rounded-lg px-3 py-2 text-sm text-[var(--color-text-muted)] transition hover:bg-white/5 hover:text-[var(--color-text)] sm:inline-flex">Dashboard</Link>
          <a href="mailto:labkom@unmuhbabel.ac.id" className="inline-flex min-h-10 items-center rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm font-medium text-[var(--color-text)] transition hover:bg-white/5">Hubungi kami</a>
        </div>
      </nav>
      <div className="mx-auto flex max-w-6xl flex-col gap-16 px-5 pb-8 pt-4 sm:gap-24 sm:px-8 sm:pt-8">
      <section className="relative overflow-hidden rounded-3xl border border-[var(--color-border)] bg-[linear-gradient(135deg,#151a28_0%,#10131b_60%,#18251f_100%)] px-5 py-10 sm:px-10 sm:py-16">
        <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl" />
        <div className="relative max-w-3xl">
          <div className="mb-6 flex flex-wrap items-center gap-3 text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">
            <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1">PetirLabs</span>
            <span className="text-[var(--color-text-muted)]">Climate technology</span>
          </div>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-[var(--color-text)] sm:text-6xl sm:leading-[1.05]">
            Pinpoint Lightning Early Warning System
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-[var(--color-text-muted)] sm:text-lg">
            Memantau cuaca dan aktivitas petir dari sensor lokal agar kampus, sekolah, dan lokasi berisiko dapat memahami kondisi lebih awal dan mengambil keputusan dengan lebih percaya diri.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/" className="inline-flex min-h-11 items-center justify-center rounded-xl bg-emerald-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300">
              Lihat dashboard
            </Link>
            <a href="mailto:labkom@unmuhbabel.ac.id" className="inline-flex min-h-11 items-center justify-center rounded-xl border border-[var(--color-border)] px-5 py-3 text-sm font-semibold text-[var(--color-text)] transition hover:bg-white/5">
              Hubungi tim
            </a>
          </div>
          <p className="mt-5 text-xs text-[var(--color-text-muted)]">University-originated climate technology venture · Labkom Universitas Muhammadiyah Bangka Belitung</p>
        </div>
      </section>

      <section className="grid gap-8 md:grid-cols-[0.9fr_1.1fr] md:items-start">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">Mengapa PetirLabs</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--color-text)] sm:text-4xl">Data petir yang bisa dipahami operator.</h2>
        </div>
        <div className="space-y-5 text-sm leading-7 text-[var(--color-text-muted)] sm:text-base">
          <p>Informasi petir sering tersebar antara sensor, catatan manual, dan data historis. PetirLabs menyatukannya dalam alur pemantauan yang lebih mudah dibaca.</p>
          <p>Produk ini sedang dikembangkan dari prototype operasional menuju solusi yang dapat dipakai berulang oleh institusi dan lokasi dengan kebutuhan pemantauan cuaca.</p>
        </div>
      </section>

      <section className="grid gap-8 rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:p-6 md:grid-cols-[1.1fr_0.9fr] md:items-center">
        <div className="relative aspect-[3/4] overflow-hidden rounded-2xl bg-black/20">
          <Image
            src="/petirlabs/field-deployment.jpg"
            alt="PetirLabs field deployment with a solar panel, environmental sensor, and visual alert equipment"
            fill
            sizes="(max-width: 768px) 100vw, 45vw"
            className="object-contain"
          />
        </div>
        <div className="px-2 pb-2 sm:px-3 md:py-4">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">Project in action</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--color-text)]">Built for real-world conditions.</h2>
          <p className="mt-4 text-sm leading-7 text-[var(--color-text-muted)] sm:text-base">Contoh deployment lapangan PetirLabs dengan panel surya, sensor lingkungan, dan perangkat indikator visual untuk mendukung pemantauan di lokasi nyata.</p>
          <p className="mt-4 text-xs leading-6 text-[var(--color-text-muted)]">Field deployment of a PetirLabs environmental monitoring station with solar power and visual alert equipment.</p>
        </div>
      </section>

      <section>
        <div className="mb-7 max-w-2xl">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">Cara kerja</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--color-text)] sm:text-4xl">Dari sensor ke konteks operasional.</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {steps.map((step) => (
            <article key={step.number} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
              <span className="font-mono text-sm text-emerald-300">{step.number}</span>
              <h3 className="mt-8 text-lg font-semibold text-[var(--color-text)]">{step.title}</h3>
              <p className="mt-3 text-sm leading-6 text-[var(--color-text-muted)]">{step.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-8 rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 sm:p-9 md:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">Untuk siapa</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--color-text)]">Mulai dari lokasi yang perlu melihat kondisi dengan jelas.</h2>
        </div>
        <ul className="space-y-3 text-sm text-[var(--color-text-muted)] sm:text-base">
          {audiences.map((audience) => (
            <li key={audience} className="flex items-center gap-3">
              <span className="h-2 w-2 rounded-full bg-emerald-300" aria-hidden="true" />
              {audience}
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-8 border-t border-[var(--color-border)] pt-10 md:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">Status produk</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--color-text)]">Dibangun dengan data nyata dan evaluasi bertahap.</h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--color-text-muted)] sm:text-base">
            PetirLabs telah melalui pengembangan awal berbasis pendanaan publik dan kini memasuki tahap deployment pelanggan awal. Fokus kami adalah menjaga data, status sensor, dan penjelasan risiko tetap dapat ditelusuri.
          </p>
        </div>
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/5 p-5">
          <p className="text-sm font-semibold text-emerald-200">Prinsip pengembangan</p>
          <p className="mt-3 text-sm leading-6 text-[var(--color-text-muted)]">AI digunakan untuk membantu analisis dan penjelasan. Pengukuran sensor, riwayat, dan status sistem tetap menjadi sumber data yang dapat diaudit.</p>
        </div>
      </section>

      <section className="flex flex-col gap-5 rounded-3xl border border-emerald-400/20 bg-emerald-400/5 px-6 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-9">
        <div>
          <p className="text-2xl font-semibold tracking-tight text-[var(--color-text)]">Ingin melihat produk berjalan?</p>
          <p className="mt-2 text-sm text-[var(--color-text-muted)]">Buka dashboard Petir atau hubungi tim untuk pembicaraan pilot.</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link href="/" className="inline-flex min-h-11 items-center justify-center rounded-xl bg-emerald-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300">Buka dashboard</Link>
          <a href="mailto:labkom@unmuhbabel.ac.id" className="inline-flex min-h-11 items-center justify-center rounded-xl border border-[var(--color-border)] px-5 py-3 text-sm font-semibold text-[var(--color-text)] transition hover:bg-white/5">Email tim</a>
        </div>
      </section>
      </div>
      <footer className="border-t border-[var(--color-border)] px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 text-sm text-[var(--color-text-muted)] sm:flex-row sm:items-center sm:justify-between">
          <span>© 2026 PetirLabs</span>
          <span>Dikembangkan sebagai venture teknologi iklim tahap awal dari Labkom Universitas Muhammadiyah Bangka Belitung</span>
        </div>
      </footer>
    </div>
  );
}
