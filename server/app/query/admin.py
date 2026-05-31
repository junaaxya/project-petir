from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_hooks import run_hooks
from app.db import get_session
from app.models.ai import AiHookResult, RetentionPolicy
from app.query.auth import verify_dashboard_user
from app.retention import run_retention

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_dashboard_user)])


@router.get("/retention/policies")
def get_retention_policies(
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    rows = session.execute(select(RetentionPolicy)).scalars().all()
    return [
        {
            "table_name": r.table_name,
            "retain_days": r.retain_days,
            "enabled": r.enabled,
            "last_pruned_utc": r.last_pruned_utc.isoformat() if r.last_pruned_utc else None,
            "rows_pruned_last": r.rows_pruned_last,
        }
        for r in rows
    ]


@router.post("/retention/run")
def trigger_retention(
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return run_retention(session)


@router.post("/ai/run")
def trigger_ai_hooks(
    node: str = Query(...),
    hours: int = Query(default=1, ge=1, le=168),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=hours)
    return run_hooks(session, node, window_start, now)


@router.get("/ai/results")
def get_ai_results(
    node: Optional[str] = Query(default=None),
    hook_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    stmt = select(AiHookResult).order_by(AiHookResult.computed_at_utc.desc()).limit(limit)
    if node:
        stmt = stmt.where(AiHookResult.node_id == node)
    if hook_type:
        stmt = stmt.where(AiHookResult.hook_type == hook_type)
    rows = session.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "hook_type": r.hook_type,
            "node_id": r.node_id,
            "computed_at_utc": r.computed_at_utc.isoformat(),
            "window_start_utc": r.window_start_utc.isoformat() if r.window_start_utc else None,
            "window_end_utc": r.window_end_utc.isoformat() if r.window_end_utc else None,
            "score": r.score,
            "label": r.label,
            "details": r.details_json,
        }
        for r in rows
    ]
