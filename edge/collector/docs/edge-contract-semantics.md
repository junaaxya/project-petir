# Petir 2 edge sensor contract semantics

## Weather Station WS3 professional frame

- `A`: wind-direction ADC value; retained as `raw_json.wind_dir_adc`.
- `B`: wind direction angle in degrees (0–360); retained as `raw_json.wind_dir_raw_deg`.
- `C`: wind frequency; retained in `raw_json`.
- `D`, `E`, `F`: instantaneous, average, and maximum wind speed in 0.1 m/s.
- `G`: real-time tipping-bucket counter (0–9999, cyclic).
- `H`: bucket count for the previous minute.
- `I`, `J`, `K`: rolling 1-minute, 1-hour, and 24-hour rainfall in 0.1 mm.

## Contract mapping

For moving air (`wind_speed_ms > 0`):

```text
wind_dir_deg  = B, normalized 360° -> 0°
wind_dir_code = floor((wind_dir_deg + 11.25) / 22.5) mod 16
```

For calm or invalid direction values, both contract direction fields are null.
The raw ADC and B degree value remain in `raw_json`.

`weather_samples.rain_mm` is the WS3 rolling one-minute value `I`. A minute
summary uses `MAX(rain_mm)`, not SUM, to avoid repeatedly counting the same
rolling window. `G`, `H`, `I`, `J`, and `K` remain in `raw_json` for future
calibration and server-side review.

## Lux freshness

A weather row receives `illuminance_lux` only when it is paired with the
following fresh `@LUX,<value>` message. `raw_json.lux_ts_utc` records the
lux receipt time. Rows without a fresh lux timestamp use a null contract lux
value; original raw sensor payload remains retained.

## Local paths

- collector: `/home/pi/petir2-collector/src/collector_runner.py`
- SQLite: `/home/pi/petir2-collector/data/petir2_edge.db`
- systemd service: `petir2-local-collector.service`
- location design: `docs/station-location-design.md`
