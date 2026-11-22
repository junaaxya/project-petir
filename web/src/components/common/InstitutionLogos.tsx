import Image from "next/image";

const LOGOS = [
  {
    src: "/brand/tut-wuri.webp",
    alt: "Tut Wuri Handayani",
    title: "Tut Wuri Handayani",
  },
  {
    src: "/brand/diktisaintek.webp",
    alt: "Diktisaintek Berdampak",
    title: "Diktisaintek Berdampak",
  },
  {
    src: "/brand/bima.webp",
    alt: "BIMA",
    title: "BIMA",
  },
  {
    src: "/brand/lppm-umbb-clean.webp",
    alt: "LPPM Universitas Muhammadiyah Bangka Belitung",
    title: "LPPM Universitas Muhammadiyah Bangka Belitung",
    wide: true,
  },
  {
    src: "/brand/umbb.webp",
    alt: "Universitas Muhammadiyah Bangka Belitung",
    title: "Universitas Muhammadiyah Bangka Belitung",
  },
] as const;

export function InstitutionLogos() {
  return (
    <div
      className="flex shrink-0 items-center gap-1 sm:gap-1.5"
      aria-label="Logo institusi pendukung"
    >
      {LOGOS.map((logo) => (
        <span
          key={logo.src}
          title={logo.title}
          className={`flex h-7 items-center justify-center bg-white p-0.5 shadow-sm ring-1 ring-black/5 sm:h-8 ${
            "wide" in logo && logo.wide
              ? "w-16 rounded-md sm:w-20"
              : "w-7 rounded-full sm:w-8"
          }`}
        >
          <Image
            src={logo.src}
            alt={logo.alt}
            width={"wide" in logo && logo.wide ? 80 : 32}
            height={32}
            className="h-full w-full object-contain"
          />
        </span>
      ))}
    </div>
  );
}
