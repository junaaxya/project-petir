import { MetricCard } from "./MetricCard";
import { WindDirectionCard } from "./WindDirectionCard";
import type { WeatherLatestMinute } from "@/lib/types";

interface OverviewGridProps {
  minute: WeatherLatestMinute | null | undefined;
  loading: boolean;
}

export function OverviewGrid({ minute, loading }: OverviewGridProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
      <MetricCard
        label="Suhu"
        value={minute?.temperature_avg}
        unit="°C"
        min={minute?.temperature_min}
        max={minute?.temperature_max}
        loading={loading}
      />
      <MetricCard
        label="Kelembapan"
        value={minute?.humidity_avg}
        unit="%"
        loading={loading}
      />
      <MetricCard
        label="Tekanan"
        value={minute?.pressure_avg}
        unit="hPa"
        loading={loading}
      />
      <MetricCard
        label="Cahaya"
        value={minute?.illuminance_avg}
        unit="lx"
        loading={loading}
      />
      <MetricCard
        label="Hujan"
        value={minute?.rain_max}
        unit="mm"
        loading={loading}
      />
      <MetricCard
        label="Angin"
        value={minute?.wind_speed_avg}
        unit="m/s"
        max={minute?.wind_speed_max}
        loading={loading}
      />
      <WindDirectionCard deg={minute?.latest_wind_dir_deg} windSpeed={minute?.wind_speed_avg} loading={loading} />
    </div>
  );
}
