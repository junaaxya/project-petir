interface EmptyStateProps {
  message: string;
  detail?: string;
}

export function EmptyState({ message, detail }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 py-8 text-center">
      <span className="text-sm font-medium text-[var(--color-text-muted)]">{message}</span>
      {detail && (
        <span className="text-xs text-[var(--color-text-muted)] opacity-70">{detail}</span>
      )}
    </div>
  );
}
