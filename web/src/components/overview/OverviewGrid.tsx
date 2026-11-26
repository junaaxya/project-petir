import { MetricCard } from "./MetricCard";
import { WindDirectionCard } from "./WindDirectionCard";
import type { NodeStatus, WeatherLatestMinute } from "@/lib/types";
import { isRealtimeUnavailable, realtimeSnapshotDetail } from "@/lib/realtime";
import { useSiteConfig } from "@/components/common/SiteConfigProvider";
import { rainOverviewLabel } from "@/lib/rainSemantics";

interface OverviewGridProps {
  minute: WeatherLatestMinute | null | undefined;
  loading: boolean;
  nodeStatus?: NodeStatus | null;
}

export function OverviewGrid({ minute, loading, nodeStatus }: OverviewGridProps) {
  const { rainSemantics } = useSiteConfig();
  const unavailable = isRealtimeUnavailable(nodeStatus);
  const detail = realtimeSnapshotDetail(nodeStatus, minute?.minute_utc);
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-4 xl:grid-cols-7">
      <MetricCard
        label="Suhu"
        value={unavailable ? null : minute?.temperature_avg}
        unit="°C"
        loading={loading}
        emptyMessage={unavailable ? "Sensor offline" : undefined}
        emptyDetail={detail}
      />
      <MetricCard
        label="Kelembapan"
        value={unavailable ? null : minute?.humidity_avg}
        unit="%"
        loading={loading}
        emptyMessage={unavailable ? "Sensor offline" : undefined}
        emptyDetail={detail}
      />
      <MetricCard
        label="Tekanan"
        value={unavailable ? null : minute?.pressure_avg}
        unit="hPa"
        loading={loading}
        emptyMessage={unavailable ? "Sensor offline" : undefined}
        emptyDetail={detail}
      />
      <MetricCard
        label="Cahaya"
        value={unavailable ? null : minute?.illuminance_avg}
        unit="lx"
        loading={loading}
        emptyMessage={unavailable ? "Sensor offline" : undefined}
        emptyDetail={detail}
      />
      <MetricCard
        label={rainOverviewLabel(rainSemantics)}
        value={unavailable ? null : minute?.rain_max}
        unit="mm"
        loading={loading}
        emptyMessage={unavailable ? "Sensor offline" : undefined}
        emptyDetail={detail}
      />
      <MetricCard
        label="Angin"
        value={unavailable ? null : minute?.wind_speed_avg}
        unit="m/s"
        loading={loading}
        emptyMessage={unavailable ? "Sensor offline" : undefined}
        emptyDetail={detail}
      />
      <WindDirectionCard deg={unavailable ? null : minute?.latest_wind_dir_deg} windSpeed={unavailable ? null : minute?.wind_speed_avg} loading={loading} />
    </div>
  );
}
