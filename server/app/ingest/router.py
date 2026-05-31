from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.ingest.auth import check_rate_limit, verify_node_token
from app.ingest.errors import IngestError
from app.ingest.service import ingest_batch
from app.models.registry import EdgeNode, SyncRun
from petir_contracts import SyncBatchEnvelope, SyncBatchResponse

router = APIRouter(prefix="/api/ingest")


def check_backpressure(node: EdgeNode) -> None:
    check_rate_limit(node)


@router.post("/sync-batch", response_model=SyncBatchResponse)
def post_sync_batch(
    body: dict[str, Any],
    node: Annotated[EdgeNode, Depends(verify_node_token)],
    session: Annotated[Session, Depends(get_session)],
) -> SyncBatchResponse:
    try:
        envelope = SyncBatchEnvelope.model_validate(body)
    except ValidationError as exc:
        raise IngestError(
            422, "INVALID_ENVELOPE", str(exc.errors()[0].get("msg", "invalid envelope"))
        ) from exc

    if envelope.node_id != node.node_id:
        raise IngestError(409, "NODE_MISMATCH", "envelope node_id does not match token")

    check_backpressure(node)
    return ingest_batch(session, node, envelope)


@router.get("/runs")
def get_runs(
    session: Annotated[Session, Depends(get_session)],
    node: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    stmt = select(SyncRun).order_by(SyncRun.received_at_utc.desc())
    if node is not None:
        stmt = stmt.where(SyncRun.node_id == node)
    if status is not None:
        stmt = stmt.where(SyncRun.status == status)
    stmt = stmt.limit(limit)

    runs = session.execute(stmt).scalars().all()
    return [
        {
            "run_id": str(r.run_id),
            "node_id": r.node_id,
            "started_at_utc": r.started_at_utc.isoformat() if r.started_at_utc else None,
            "received_at_utc": r.received_at_utc.isoformat() if r.received_at_utc else None,
            "status": r.status,
            "tables_count": r.tables_count,
            "rows_accepted": r.rows_accepted,
            "rows_rejected": r.rows_rejected,
            "duration_ms": r.duration_ms,
            "error_detail": r.error_detail,
        }
        for r in runs
    ]
