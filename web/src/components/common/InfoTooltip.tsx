interface InfoTooltipProps {
  text: string;
  label?: string;
}

export function InfoTooltip({ text, label }: InfoTooltipProps) {
  return (
    <span className="group relative inline-flex items-center">
      <span
        tabIndex={0}
        role="button"
        aria-label={label ?? text}
        className="inline-flex h-4 w-4 cursor-default select-none items-center justify-center rounded-full text-[10px] font-semibold leading-none text-[var(--color-text-muted)] ring-1 ring-[var(--color-border)] transition-colors hover:text-[var(--color-text)] focus:outline-none focus:ring-blue-500"
      >
        ⓘ
      </span>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 w-56 -translate-x-1/2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs leading-relaxed text-[var(--color-text)] opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 whitespace-normal"
      >
        {text}
      </span>
    </span>
  );
}
