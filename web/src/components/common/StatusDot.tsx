import type { NodeStatus, WeatherStatus } from "@/lib/types";

type DotStatus = NodeStatus | WeatherStatus;

const dotColor: Record<string, string> = {
  fresh: "bg-[#16a34a]",
  ok: "bg-[#16a34a]",
  stale: "bg-[#d97706]",
  warn: "bg-[#d97706]",
  degraded: "bg-[#d97706]",
  offline: "bg-[#dc2626]",
  invalid: "bg-[#dc2626]",
  no_data: "bg-[#6b7280]",
};

interface StatusDotProps {
  status: DotStatus;
  pulse?: boolean;
}

export function StatusDot({ status, pulse = false }: StatusDotProps) {
  const color = dotColor[status] ?? dotColor["no_data"];
  return (
    <span className="relative inline-flex h-2.5 w-2.5">
      {pulse && status === "fresh" && (
        <span
          className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${color}`}
        />
      )}
      <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${color}`} />
    </span>
  );
}
