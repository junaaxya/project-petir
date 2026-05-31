from __future__ import annotations

import math
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://petir:petir@localhost:55432/petir"
)

from app.ingest.auth import hash_token
from app.models.lightning import LightningEvent, LightningMinuteSummary
from app.models.ops import SystemEvent, WeatherQualityEvent
from app.models.registry import EdgeNode, SyncRun
from app.models.weather import WeatherMinuteSummary

NODE_ID = "rpi-lab-01"
NODE_TOKEN = "dev-token"
DB_EPOCH = uuid.uuid4()


def seed() -> None:
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url, future=True)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    s = maker()

    s.query(WeatherMinuteSummary).delete()
    s.query(LightningMinuteSummary).delete()
    s.query(LightningEvent).delete()
    s.query(WeatherQualityEvent).delete()
    s.query(SystemEvent).delete()
    s.query(SyncRun).delete()
    s.query(EdgeNode).filter_by(node_id=NODE_ID).delete()
    s.commit()

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    node = EdgeNode(
        node_id=NODE_ID,
        name="Lab Rooftop Station",
        location="Building A rooftop",
        api_token_hash=hash_token(NODE_TOKEN),
        contract_version="1.0.0",
        last_seen_utc=now,
        enabled=True,
    )
    s.add(node)

    run = SyncRun(
        run_id=uuid.uuid4(),
        node_id=NODE_ID,
        started_at_utc=now - timedelta(seconds=30),
        status="accepted",
        tables_count=4,
        rows_accepted=1440,
        rows_rejected=0,
        duration_ms=820,
    )
    s.add(run)
    s.flush()

    minutes = 24 * 60
    for i in range(minutes):
        ts = now - timedelta(minutes=(minutes - i))
        hour_frac = ts.hour + ts.minute / 60.0
        temp = 27.0 + 4.0 * math.sin((hour_frac - 9) / 24 * 2 * math.pi) + random.uniform(-0.4, 0.4)
        humidity = 70.0 - 15.0 * math.sin((hour_frac - 9) / 24 * 2 * math.pi) + random.uniform(-2, 2)
        pressure = 1009.0 + 2.0 * math.sin(hour_frac / 24 * 2 * math.pi) + random.uniform(-0.3, 0.3)
        illum = max(0.0, 800.0 * math.sin((hour_frac - 6) / 12 * math.pi)) if 6 <= hour_frac <= 18 else 0.0
        rain = round(random.choice([0, 0, 0, 0, 0, 0.2, 0.5, 1.2]), 1) if 13 <= hour_frac <= 16 else 0.0
        wind = abs(2.0 + 1.5 * math.sin(hour_frac / 6) + random.uniform(-0.5, 1.0))
        wind_dir = (180 + 60 * math.sin(hour_frac / 24 * 2 * math.pi) + random.uniform(-30, 30)) % 360

        s.add(
            WeatherMinuteSummary(
                node_id=NODE_ID,
                db_epoch=DB_EPOCH,
                ingest_run_id=run.run_id,
                change_seq=i + 1,
                minute_utc=ts,
                source="arduino",
                device="weather-01",
                sample_count=12,
                metric_sample_count=12,
                valid_sample_count=12,
                status="ok",
                degraded=False,
                temperature_avg=round(temp, 2),
                temperature_min=round(temp - random.uniform(0.2, 0.8), 2),
                temperature_max=round(temp + random.uniform(0.2, 0.8), 2),
                humidity_avg=round(humidity, 1),
                pressure_avg=round(pressure, 1),
                illuminance_avg=round(illum, 1),
                rain_max=rain,
                wind_speed_avg=round(wind, 2),
                wind_speed_max=round(wind + random.uniform(0.5, 2.0), 2),
                latest_wind_dir_deg=round(wind_dir, 0),
                last_sample_ts_utc=ts,
                updated_at_utc=ts,
            )
        )

    storm_start = now - timedelta(hours=3)
    seq = 1
    edge = 1
    for m in range(40):
        ts = storm_start + timedelta(minutes=m)
        in_storm = 5 <= m <= 30
        lc = random.randint(1, 6) if in_storm else 0
        dc = random.randint(0, 4) if in_storm else random.randint(0, 1)
        last_event = None
        last_dist = None
        max_energy = None
        if lc > 0:
            for _ in range(lc):
                dist = round(random.uniform(3, 28), 1)
                en = random.randint(120000, 900000)
                ev_ts = ts + timedelta(seconds=random.randint(0, 59))
                s.add(
                    LightningEvent(
                        node_id=NODE_ID,
                        db_epoch=DB_EPOCH,
                        ingest_run_id=run.run_id,
                        edge_id=edge,
                        ts_pi_utc=ev_ts,
                        source="arduino",
                        device="as3935",
                        sensor="AS3935",
                        event_type="lightning",
                        distance_km=dist,
                        energy_raw=en,
                        created_at_utc=ev_ts,
                    )
                )
                edge += 1
                last_event = ev_ts
                last_dist = dist
                max_energy = max(max_energy or 0, en)

        status = "activity" if lc > 0 else ("disturber" if dc > 0 else "quiet")
        s.add(
            LightningMinuteSummary(
                node_id=NODE_ID,
                db_epoch=DB_EPOCH,
                ingest_run_id=run.run_id,
                change_seq=seq,
                minute_utc=ts,
                source="arduino",
                device="as3935",
                lightning_count=lc,
                disturber_count=dc,
                noise_window_count=random.randint(0, 2),
                noise_event_count=0,
                status=status,
                last_event_ts_utc=last_event,
                last_distance_km=last_dist,
                max_energy_raw=max_energy,
                updated_at_utc=ts,
            )
        )
        seq += 1

    levels = ["info", "info", "info", "warn", "info", "error", "info", "warn"]
    types = ["boot", "heartbeat", "sync_ok", "sensor_reconnect", "heartbeat", "ingest_retry", "heartbeat", "high_humidity"]
    for i in range(24):
        ts = now - timedelta(hours=i)
        s.add(
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=DB_EPOCH,
                ingest_run_id=run.run_id,
                edge_id=10000 + i,
                ts_pi_utc=ts,
                source="edge",
                level=levels[i % len(levels)],
                event_type=types[i % len(types)],
                message=f"{types[i % len(types)]} at {ts.strftime('%H:%M')}",
                created_at_utc=ts,
            )
        )

    q_status = ["ok", "ok", "warn", "ok", "invalid", "warn", "ok", "ok"]
    reasons = ["", "", "humidity_spike", "", "out_of_range", "stale_reading", "", ""]
    for i in range(16):
        ts = now - timedelta(hours=i * 1.3)
        st = q_status[i % len(q_status)]
        if st == "ok":
            continue
        s.add(
            WeatherQualityEvent(
                node_id=NODE_ID,
                db_epoch=DB_EPOCH,
                ingest_run_id=run.run_id,
                edge_id=20000 + i,
                ts_pi_utc=ts,
                minute_utc=ts.replace(second=0, microsecond=0),
                sample_ts_utc=ts,
                source="arduino",
                device="weather-01",
                quality_status=st,
                reason_codes=reasons[i % len(reasons)],
                message=f"quality {st}: {reasons[i % len(reasons)] or 'n/a'}",
                created_at_utc=ts,
            )
        )

    s.commit()
    s.close()
    print(f"Seeded node={NODE_ID}: 1440 weather minutes, lightning storm, 24 system events, quality events.")


if __name__ == "__main__":
    seed()
