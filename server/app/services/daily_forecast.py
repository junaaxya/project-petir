from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any, Literal, Mapping, Sequence
from zoneinfo import ZoneInfo

ForecastKind = Literal["petir", "hujan", "angin"]
ForecastLevel = Literal["rendah", "sedang", "tinggi"]

WIB = ZoneInfo("Asia/Jakarta")


@dataclass(frozen=True)
class ForecastRanges:
    baseline_start_utc: datetime
    today_start_utc: datetime
    tomorrow_start_utc: datetime
    today_label: str
    local_date: str


@dataclass(frozen=True)
class BaselineStats:
    humidity_high: float
    humidity_rise_60: float
    pressure_drop_180: float
    pressure_drop_60: float
    temp_drop_60: float
    bright_lux: float
    lux_drop_pct_30: float
    wind_rise_30: float
    wind_high: float
    temp_hot: float


@dataclass(frozen=True)
class ScoredPoint:
    bucket: datetime
    petir: float
    hujan: float
    angin: float
    petir_reasons: tuple[str, ...]
    hujan_reasons: tuple[str, ...]
    angin_reasons: tuple[str, ...]


@dataclass(frozen=True)
class FutureHourScore:
    hour: int
    petir: float
    hujan: float
    angin: float


@dataclass(frozen=True)
class ForecastSnapshot:
    kind: ForecastKind
    label: str
    score: float
    level: ForecastLevel
    peak_window: str | None
    reasons: list[str]


def forecast_ranges_wib(now: datetime) -> ForecastRanges:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    local_now = now.astimezone(WIB)
    today_local = datetime.combine(local_now.date(), time.min, tzinfo=WIB)
    tomorrow_local = today_local + timedelta(days=1)
    baseline_local = today_local - timedelta(days=7)
    return ForecastRanges(
        baseline_start_utc=baseline_local.astimezone(timezone.utc),
        today_start_utc=today_local.astimezone(timezone.utc),
        tomorrow_start_utc=tomorrow_local.astimezone(timezone.utc),
        today_label=local_now.strftime("%d-%m-%Y"),
        local_date=local_now.date().isoformat(),
    )


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _field(row: Mapping[str, Any], *names: str) -> float | None:
    for name in names:
        value = _number(row.get(name))
        if value is not None:
            return value
    return None


def _bucket(row: Mapping[str, Any]) -> datetime:
    value = row.get("bucket")
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("forecast row bucket must be an ISO timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("forecast row bucket must be timezone-aware")
    return parsed


def _humidity(row: Mapping[str, Any]) -> float | None:
    return _field(row, "humidity_avg", "humidity_pct")


def _pressure(row: Mapping[str, Any]) -> float | None:
    return _field(row, "pressure_avg", "pressure_hpa")


def _temperature(row: Mapping[str, Any]) -> float | None:
    return _field(row, "temperature_avg", "temperature_c")


def _illuminance(row: Mapping[str, Any]) -> float | None:
    return _field(row, "illuminance_avg", "illuminance_lux")


def _rain(row: Mapping[str, Any]) -> float | None:
    return _field(row, "rain_max", "rain_mm")


def _wind_max(row: Mapping[str, Any]) -> float | None:
    return _field(row, "wind_speed_max", "wind_speed_avg", "wind_speed_ms")


def percentile(values: Sequence[float], q: float, fallback: float) -> float:
    clean = sorted(value for value in values if math.isfinite(value))
    if not clean:
        return fallback
    index = min(len(clean) - 1, max(0, math.floor(q * (len(clean) - 1))))
    return clean[index]


def _positive_diffs(
    values: Sequence[float | None],
    lag: int,
    transform,
) -> list[float]:
    diffs: list[float] = []
    for index in range(lag, len(values)):
        current = values[index]
        previous = values[index - lag]
        if current is None or previous is None:
            continue
        diff = float(transform(current, previous))
        if math.isfinite(diff) and diff > 0:
            diffs.append(diff)
    return diffs


def build_baseline(series: Sequence[Mapping[str, Any]]) -> BaselineStats:
    humidity = [_humidity(row) for row in series]
    pressure = [_pressure(row) for row in series]
    temperature = [_temperature(row) for row in series]
    illuminance = [_illuminance(row) for row in series]
    wind = [_wind_max(row) for row in series]

    return BaselineStats(
        humidity_high=max(80, percentile([v for v in humidity if v is not None], 0.9, 85)),
        humidity_rise_60=max(3.5, percentile(_positive_diffs(humidity, 60, lambda c, p: c - p), 0.9, 5.5)),
        pressure_drop_180=max(1.2, percentile(_positive_diffs(pressure, 180, lambda c, p: p - c), 0.9, 2)),
        pressure_drop_60=max(0.5, percentile(_positive_diffs(pressure, 60, lambda c, p: p - c), 0.9, 1)),
        temp_drop_60=max(0.8, percentile(_positive_diffs(temperature, 60, lambda c, p: p - c), 0.9, 1.5)),
        bright_lux=max(20_000, percentile([v for v in illuminance if v is not None], 0.75, 20_000)),
        lux_drop_pct_30=max(
            55,
            percentile(
                _positive_diffs(illuminance, 30, lambda c, p: ((p - c) / max(p, 1)) * 100),
                0.9,
                75,
            ),
        ),
        wind_rise_30=max(0.06, percentile(_positive_diffs(wind, 30, lambda c, p: c - p), 0.9, 0.09)),
        wind_high=max(0.2, percentile([v for v in wind if v is not None], 0.9, 0.31)),
        temp_hot=max(31, percentile([v for v in temperature if v is not None], 0.9, 35)),
    )


def score_series(series: Sequence[Mapping[str, Any]], baseline: BaselineStats) -> list[ScoredPoint]:
    scored: list[ScoredPoint] = []
    for index, row in enumerate(series):
        prev_30 = series[index - 30] if index >= 30 else None
        prev_60 = series[index - 60] if index >= 60 else None
        prev_180 = series[index - 180] if index >= 180 else None

        humidity = _humidity(row)
        pressure = _pressure(row)
        temperature = _temperature(row)
        illuminance = _illuminance(row)
        wind_max = _wind_max(row) or 0
        rain = _rain(row) or 0

        prev_humidity = _humidity(prev_60) if prev_60 else None
        prev_pressure_180 = _pressure(prev_180) if prev_180 else None
        prev_pressure_60 = _pressure(prev_60) if prev_60 else None
        prev_temperature = _temperature(prev_60) if prev_60 else None
        prev_lux_30 = _illuminance(prev_30) if prev_30 else None
        prev_wind_30 = _wind_max(prev_30) if prev_30 else None

        humidity_rise = humidity - (prev_humidity if prev_humidity is not None else humidity) if humidity is not None and prev_60 else None
        pressure_drop_180 = (prev_pressure_180 if prev_pressure_180 is not None else pressure) - pressure if pressure is not None and prev_180 else None
        pressure_drop_60 = (prev_pressure_60 if prev_pressure_60 is not None else pressure) - pressure if pressure is not None and prev_60 else None
        temp_drop_60 = (prev_temperature if prev_temperature is not None else temperature) - temperature if temperature is not None and prev_60 else None
        lux_drop_pct_30 = (
            ((prev_lux_30 - illuminance) / prev_lux_30) * 100
            if illuminance is not None and prev_lux_30 is not None and prev_lux_30 > 0
            else None
        )
        wind_rise_30 = wind_max - (prev_wind_30 if prev_wind_30 is not None else wind_max) if prev_30 else None

        petir = hujan = angin = 0.0
        petir_reasons: list[str] = []
        hujan_reasons: list[str] = []
        angin_reasons: list[str] = []

        if humidity is not None and humidity >= baseline.humidity_high:
            petir += 2
            hujan += 2
            petir_reasons.append("kelembapan masih tinggi")
            hujan_reasons.append("kelembapan masih tinggi")
        if humidity_rise is not None and humidity_rise >= baseline.humidity_rise_60:
            petir += 1
            hujan += 1
            petir_reasons.append("kelembapan naik cepat")
            hujan_reasons.append("kelembapan naik cepat")
        if pressure_drop_180 is not None and pressure_drop_180 >= baseline.pressure_drop_180:
            petir += 2
            hujan += 1
            petir_reasons.append("tekanan terus menurun")
            hujan_reasons.append("tekanan terus menurun")
        if temp_drop_60 is not None and temp_drop_60 >= baseline.temp_drop_60:
            petir += 1
            hujan += 1
            petir_reasons.append("suhu mulai turun")
            hujan_reasons.append("suhu mulai turun")
        if (
            prev_lux_30 is not None
            and prev_lux_30 >= baseline.bright_lux
            and lux_drop_pct_30 is not None
            and lux_drop_pct_30 >= baseline.lux_drop_pct_30
        ):
            petir += 1
            hujan += 2
            petir_reasons.append("cahaya turun mendadak")
            hujan_reasons.append("cahaya turun mendadak")
        if wind_rise_30 is not None and wind_rise_30 >= baseline.wind_rise_30:
            petir += 1
            angin += 2
            petir_reasons.append("angin mulai meningkat")
            angin_reasons.append("angin mulai meningkat")

        local_hour = _bucket(row).astimezone(WIB).hour
        if 12 <= local_hour <= 18:
            petir += 1
            petir_reasons.append("masuk jam rawan siang-sore")
        if wind_max >= baseline.wind_high:
            angin += 2
            angin_reasons.append("kecepatan angin cukup tinggi")
        if pressure_drop_60 is not None and pressure_drop_60 >= baseline.pressure_drop_60:
            angin += 1
            angin_reasons.append("tekanan turun dalam 1 jam terakhir")
        if temperature is not None and temperature >= baseline.temp_hot:
            angin += 1
            angin_reasons.append("udara siang cukup panas")
        if rain > 0:
            hujan += 2
            hujan_reasons.append("sensor hujan sudah mulai aktif")

        scored.append(
            ScoredPoint(
                bucket=_bucket(row),
                petir=petir,
                hujan=hujan,
                angin=angin,
                petir_reasons=tuple(petir_reasons),
                hujan_reasons=tuple(hujan_reasons),
                angin_reasons=tuple(angin_reasons),
            )
        )
    return scored


def _average(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def build_future_hour_scores(
    baseline_scored: Sequence[ScoredPoint],
    today_scored: Sequence[ScoredPoint],
    *,
    now: datetime,
) -> list[FutureHourScore]:
    local_now = now.astimezone(WIB)
    start_hour = min(local_now.hour + 1, 23) if local_now.minute > 0 else local_now.hour
    hourly: dict[int, dict[ForecastKind, list[float]]] = {}
    for point in baseline_scored:
        hour = point.bucket.astimezone(WIB).hour
        slot = hourly.setdefault(hour, {"petir": [], "hujan": [], "angin": []})
        slot["petir"].append(point.petir)
        slot["hujan"].append(point.hujan)
        slot["angin"].append(point.angin)

    recent_start = now - timedelta(minutes=90)
    recent = [point for point in today_scored if point.bucket >= recent_start]
    momentum = {
        "petir": max([point.petir for point in recent] + [0]),
        "hujan": max([point.hujan for point in recent] + [0]),
        "angin": max([point.angin for point in recent] + [0]),
    }

    results: list[FutureHourScore] = []
    for hour in range(start_hour, 24):
        slot = hourly.get(hour, {"petir": [], "hujan": [], "angin": []})
        distance = hour - start_hour
        decay = 1 if distance == 0 else 0.72 if distance == 1 else 0.45 if distance == 2 else 0.25 if distance == 3 else 0.1
        results.append(
            FutureHourScore(
                hour=hour,
                petir=_average(slot["petir"]) + momentum["petir"] * decay,
                hujan=_average(slot["hujan"]) + momentum["hujan"] * decay,
                angin=_average(slot["angin"]) + momentum["angin"] * decay,
            )
        )
    return results


def level_from_score(kind: ForecastKind, score: float) -> ForecastLevel:
    if kind == "petir":
        return "tinggi" if score >= 5 else "sedang" if score >= 2.5 else "rendah"
    if kind == "hujan":
        return "tinggi" if score >= 4.5 else "sedang" if score >= 2.5 else "rendah"
    return "tinggi" if score >= 3.5 else "sedang" if score >= 2 else "rendah"


def _kind_score(point: ScoredPoint | FutureHourScore, kind: ForecastKind) -> float:
    return getattr(point, kind)


def _kind_reasons(point: ScoredPoint, kind: ForecastKind) -> tuple[str, ...]:
    return getattr(point, f"{kind}_reasons")


def _format_hour_window(hour: int) -> str:
    return f"{hour:02d}.00–{min(hour + 1, 23):02d}.59"


def summarize(
    kind: ForecastKind,
    today_scored: Sequence[ScoredPoint],
    future_hours: Sequence[FutureHourScore],
    *,
    now: datetime,
) -> ForecastSnapshot:
    label = "Potensi Petir" if kind == "petir" else "Potensi Hujan" if kind == "hujan" else "Potensi Angin Kencang"
    if not future_hours:
        return ForecastSnapshot(kind, label, 0, "rendah", None, ["Sisa hari ini sudah tidak panjang"])

    recent_start = now - timedelta(minutes=120)
    recent = [point for point in today_scored if point.bucket >= recent_start]
    recent_top = max(recent, key=lambda point: (_kind_score(point, kind), point.bucket), default=None)
    top_hour = max(future_hours, key=lambda point: (_kind_score(point, kind), -point.hour))
    score = _kind_score(top_hour, kind)
    level = level_from_score(kind, score)
    reasons = list(_kind_reasons(recent_top, kind)[:2]) if recent_top else []

    if not reasons:
        if level == "rendah":
            reasons.append(
                "belum terlihat sinyal petir yang kuat untuk sisa hari ini"
                if kind == "petir"
                else "belum terlihat sinyal hujan yang kuat untuk sisa hari ini"
                if kind == "hujan"
                else "belum terlihat sinyal angin kencang yang kuat untuk sisa hari ini"
            )
        else:
            reasons.append(
                "potensi meningkat di jam berikutnya"
                if kind == "petir"
                else "potensi hujan masih terbuka di jam berikutnya"
                if kind == "hujan"
                else "angin berpotensi menguat di jam berikutnya"
            )

    return ForecastSnapshot(
        kind=kind,
        label=label,
        score=score,
        level=level,
        peak_window=None if level == "rendah" else _format_hour_window(top_hour.hour),
        reasons=reasons,
    )


def calculate_daily_forecast(
    today_series: Sequence[Mapping[str, Any]],
    baseline_series: Sequence[Mapping[str, Any]],
    *,
    now: datetime,
) -> list[ForecastSnapshot]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not today_series:
        return []
    baseline_source = baseline_series if baseline_series else today_series
    baseline = build_baseline(baseline_source)
    today_scored = score_series(today_series, baseline)
    baseline_scored = score_series(baseline_source, baseline)
    future = build_future_hour_scores(baseline_scored, today_scored, now=now)
    return [
        summarize("petir", today_scored, future, now=now),
        summarize("hujan", today_scored, future, now=now),
        summarize("angin", today_scored, future, now=now),
    ]
