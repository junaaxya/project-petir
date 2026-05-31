from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.errors import IngestError
from app.ingest.upserts import batch_max_cursor, cursor_strategy, upsert_rows
from app.models.registry import EdgeNode, SyncCursor, SyncRun
from petir_contracts import (
    CONTRACT_VERSION,
    Cursor,
    CursorStrategy,
    IngestStatus,
    ROW_MODELS,
    RejectedRow,
    SyncBatchEnvelope,
    SyncBatchResponse,
)


def _major(version: str) -> str:
    return version.split(".", 1)[0]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_rows(
    table: str, rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[RejectedRow]]:
    model = ROW_MODELS[table]
    valid: list[dict[str, Any]] = []
    rejected: list[RejectedRow] = []
    for index, raw in enumerate(rows):
        try:
            parsed = model.model_validate(raw)
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = first.get("loc") or ()
            field = str(loc[-1]) if loc else None
            rejected.append(
                RejectedRow(index=index, reason=first.get("msg", "invalid"), field=field)
            )
            continue
        valid.append(parsed.model_dump(mode="json"))
    return valid, rejected


def _build_status(accepted: int, rejected_count: int) -> IngestStatus:
    if rejected_count == 0:
        return IngestStatus.accepted
    if accepted > 0:
        return IngestStatus.partial
    return IngestStatus.rejected


def ingest_batch(
    session: Session, node: EdgeNode, envelope: SyncBatchEnvelope
) -> SyncBatchResponse:
    if _major(envelope.contract_version) != _major(CONTRACT_VERSION):
        raise IngestError(
            426,
            "CONTRACT_INCOMPATIBLE",
            f"major contract version {envelope.contract_version} != {CONTRACT_VERSION}",
        )

    table = envelope.table.value
    run_id = uuid.UUID(envelope.run_id)
    db_epoch = uuid.UUID(envelope.db_epoch)
    strategy = cursor_strategy(table)

    valid_rows, rejected = _validate_rows(table, envelope.rows)
    rejected_count = len(rejected)

    try:
        run = session.get(SyncRun, run_id)
        started_at = None
        duration_ms = None
        if envelope.run is not None:
            if envelope.run.started_at_utc is not None:
                started_at = datetime.fromisoformat(envelope.run.started_at_utc)
            duration_ms = envelope.run.duration_ms
        if run is None:
            run = SyncRun(
                run_id=run_id,
                node_id=node.node_id,
                started_at_utc=started_at,
                received_at_utc=_now(),
                status=IngestStatus.accepted.value,
                tables_count=0,
                rows_accepted=0,
                rows_rejected=0,
                duration_ms=duration_ms,
            )
            session.add(run)
        session.flush()

        accepted = upsert_rows(
            session, node.node_id, db_epoch, run_id, table, valid_rows
        )

        cursor = session.get(SyncCursor, (node.node_id, table))
        current = None
        if cursor is not None:
            # db_epoch reset: a new epoch means the edge SQLite was reflashed and its
            # edge_id/change_seq sequence restarted from 1; the stored cursor now points
            # into a dead sequence and must be cleared so old keys are not skipped.
            if cursor.db_epoch is not None and cursor.db_epoch != db_epoch:
                cursor.last_edge_id = None
                cursor.last_change_seq = None
            current = (
                cursor.last_edge_id
                if strategy is CursorStrategy.append
                else cursor.last_change_seq
            )

        # Quarantine cursor advance: the new cursor is the MAX cursor key across ALL raw
        # rows in the batch, including rows rejected for other reasons. This guarantees a
        # poison row can never stall the stream; the cursor moves past it on the next ACK.
        batch_max = batch_max_cursor(table, envelope.rows)
        if batch_max is None:
            new_value = current
        elif current is None:
            new_value = batch_max
        else:
            new_value = max(current, batch_max)

        if cursor is None:
            cursor = SyncCursor(
                node_id=node.node_id,
                table_name=table,
                rows_total=0,
            )
            session.add(cursor)
        if strategy is CursorStrategy.append:
            cursor.last_edge_id = new_value
        else:
            cursor.last_change_seq = new_value
        cursor.db_epoch = db_epoch
        cursor.rows_total = (cursor.rows_total or 0) + accepted
        cursor.last_run_id = run_id
        cursor.checkpoint_at_utc = _now()

        run.tables_count = (run.tables_count or 0) + 1
        run.rows_accepted = (run.rows_accepted or 0) + accepted
        run.rows_rejected = (run.rows_rejected or 0) + rejected_count
        run.status = _build_status(run.rows_accepted, run.rows_rejected).value
        if duration_ms is not None:
            run.duration_ms = duration_ms

        node.last_seen_utc = _now()
        node.contract_version = envelope.contract_version

        session.commit()
    except Exception:
        session.rollback()
        raise

    if strategy is CursorStrategy.append:
        accepted_cursor = Cursor(strategy=CursorStrategy.append, last_edge_id=new_value)
    else:
        accepted_cursor = Cursor(
            strategy=CursorStrategy.summary, last_change_seq=new_value
        )

    return SyncBatchResponse(
        run_id=envelope.run_id,
        table=envelope.table,
        status=_build_status(accepted, rejected_count),
        accepted=accepted,
        rejected=rejected,
        accepted_cursor=accepted_cursor,
        server_contract_version=CONTRACT_VERSION,
    )
