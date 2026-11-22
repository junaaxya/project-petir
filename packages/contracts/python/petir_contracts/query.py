from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


ForecastKind = Literal["petir", "hujan", "angin"]
ForecastLevel = Literal["rendah", "sedang", "tinggi"]
ForecastStatus = Literal["available", "insufficient_data", "stale_data"]


class DailyForecastItem(BaseModel):
    kind: ForecastKind
    label: str
    score: float
    level: ForecastLevel
    peak_window: str | None
    reasons: list[str]


class DailyForecastResponse(BaseModel):
    node_id: str | None
    forecast_date_wib: str
    today_label: str
    timezone: Literal["Asia/Jakarta"] = "Asia/Jakarta"
    computed_at_utc: str
    status: ForecastStatus
    sample_count: int
    latest_sample_utc: str | None
    items: list[DailyForecastItem]


class LightningEventItem(BaseModel):
    edge_id: int
    ts_pi_utc: str
    event_type: Literal["lightning", "disturber", "noise"] | None
    distance_km: float | None
    energy_raw: int | None
    noise_level: int | None
    source: str | None
    device: str | None


class PaginationMeta(BaseModel):
    count: int
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_prev: bool
    has_next: bool
    requested_limit: int | None = None
    scope: str | None = None


class LightningEventsResponse(BaseModel):
    node_id: str | None
    items: list[LightningEventItem]
    meta: PaginationMeta


class LightningEventsExportMeta(BaseModel):
    count: int
    scope: Literal["all_filtered"]


class LightningEventsExportResponse(BaseModel):
    node_id: str | None
    items: list[LightningEventItem]
    meta: LightningEventsExportMeta
