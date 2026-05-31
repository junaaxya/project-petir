from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.ai import AiHookResult


@dataclass
class HookInput:
    node_id: str
    window_start: datetime
    window_end: datetime
    session: Session


@dataclass
class HookOutput:
    score: Optional[float] = None
    label: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class AiHook(ABC):
    hook_type: str

    @abstractmethod
    def compute(self, inp: HookInput) -> HookOutput:
        ...


class WeatherAnomalyHook(AiHook):
    hook_type = "weather_anomaly"

    def compute(self, inp: HookInput) -> HookOutput:
        from sqlalchemy import select, func
        from app.models.weather import WeatherMinuteSummary

        stmt = (
            select(
                func.avg(WeatherMinuteSummary.temperature_avg).label("mean"),
                func.stddev(WeatherMinuteSummary.temperature_avg).label("std"),
            )
            .where(WeatherMinuteSummary.node_id == inp.node_id)
            .where(WeatherMinuteSummary.minute_utc >= inp.window_start)
            .where(WeatherMinuteSummary.minute_utc < inp.window_end)
        )
        row = inp.session.execute(stmt).one_or_none()
        if row is None or row.mean is None:
            return HookOutput(score=None, label="insufficient_data")

        mean, std = float(row.mean), float(row.std) if row.std else 0.0
        anomaly_score = std / max(abs(mean), 0.01)
        label = "normal" if anomaly_score < 0.3 else "anomalous"
        return HookOutput(
            score=anomaly_score,
            label=label,
            details={"mean": mean, "std": std},
        )


class LightningRiskHook(AiHook):
    hook_type = "lightning_risk"

    def compute(self, inp: HookInput) -> HookOutput:
        from sqlalchemy import select, func
        from app.models.lightning import LightningEvent

        stmt = (
            select(
                func.count().label("event_count"),
                func.min(LightningEvent.distance_km).label("min_distance"),
                func.avg(LightningEvent.energy_raw).label("avg_energy"),
            )
            .where(LightningEvent.node_id == inp.node_id)
            .where(LightningEvent.ts_pi_utc >= inp.window_start)
            .where(LightningEvent.ts_pi_utc < inp.window_end)
            .where(LightningEvent.event_type == "lightning")
        )
        row = inp.session.execute(stmt).one_or_none()
        if row is None or row.event_count == 0:
            return HookOutput(score=0.0, label="no_activity")

        count = int(row.event_count)
        min_dist = float(row.min_distance) if row.min_distance else 40.0
        proximity_factor = max(0.0, 1.0 - (min_dist / 40.0))
        frequency_factor = min(1.0, count / 20.0)
        risk_score = 0.6 * proximity_factor + 0.4 * frequency_factor

        if risk_score > 0.7:
            label = "high"
        elif risk_score > 0.3:
            label = "moderate"
        else:
            label = "low"

        return HookOutput(
            score=risk_score,
            label=label,
            details={
                "event_count": count,
                "min_distance_km": min_dist,
                "avg_energy": float(row.avg_energy) if row.avg_energy else None,
            },
        )


REGISTERED_HOOKS: list[AiHook] = [
    WeatherAnomalyHook(),
    LightningRiskHook(),
]


def run_hooks(session: Session, node_id: str, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
    inp = HookInput(
        node_id=node_id,
        window_start=window_start,
        window_end=window_end,
        session=session,
    )
    results = []
    for hook in REGISTERED_HOOKS:
        output = hook.compute(inp)
        record = AiHookResult(
            hook_type=hook.hook_type,
            node_id=node_id,
            window_start_utc=window_start,
            window_end_utc=window_end,
            score=output.score,
            label=output.label,
            details_json=output.details,
        )
        session.add(record)
        results.append({
            "hook_type": hook.hook_type,
            "score": output.score,
            "label": output.label,
            "details": output.details,
        })
    session.commit()
    return results
