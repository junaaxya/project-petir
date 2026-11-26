from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


ForecastKind = Literal["petir", "hujan", "angin"]
ForecastLevel = Literal["rendah", "sedang", "tinggi"]
ForecastStatus = Literal["available", "insufficient_data", "stale_data"]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]


def _date_input(value):
    if not isinstance(value, (str, date)):
        raise ValueError("date must be an ISO 8601 string")
    return value


def _datetime_input(value):
    if value is not None and not isinstance(value, (str, datetime)):
        raise ValueError("datetime must be an RFC 3339 string")
    return value


JsonDate = Annotated[date, BeforeValidator(_date_input)]
JsonDateTime = Annotated[datetime, BeforeValidator(_datetime_input)]


class _QueryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class DailyForecastItem(_QueryModel):
    kind: ForecastKind
    label: str
    score: float
    level: ForecastLevel
    peak_window: str | None
    reasons: list[str]


class DailyForecastResponse(_QueryModel):
    node_id: str | None
    forecast_date_wib: JsonDate
    today_label: str
    timezone: Literal["Asia/Jakarta"] = "Asia/Jakarta"
    computed_at_utc: JsonDateTime
    status: ForecastStatus
    sample_count: NonNegativeInt
    latest_sample_utc: JsonDateTime | None
    items: list[DailyForecastItem]


class LightningEventItem(_QueryModel):
    event_id: str | None = None
    edge_id: int | None = None
    ts_pi_utc: JsonDateTime
    event_type: Literal["lightning", "disturber", "noise"] | None
    distance_km: float | None
    energy_raw: int | None = None
    noise_level: int | None = None
    source: str | None = None
    device: str | None = None


class PaginationMeta(_QueryModel):
    count: NonNegativeInt
    page: PositiveInt
    page_size: PositiveInt
    total_items: NonNegativeInt
    total_pages: PositiveInt
    has_prev: bool
    has_next: bool
    requested_limit: PositiveInt | None = None
    scope: str | None = None


class LightningEventsResponse(_QueryModel):
    node_id: str | None
    items: list[LightningEventItem]
    meta: PaginationMeta


class LightningEventsExportMeta(_QueryModel):
    count: NonNegativeInt
    scope: Literal["all_filtered"]


class LightningEventsExportResponse(_QueryModel):
    node_id: str | None
    items: list[LightningEventItem]
    meta: LightningEventsExportMeta
