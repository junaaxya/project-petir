from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.registry import EdgeNode
from app.models.siren import SirenAuditRequest, SirenAuditStatusUpdate
from app.query.downsample import parse_range
from app.query.freshness import age_seconds, status_for_node
from app.schemas.siren import SirenAuditRequestCreate, SirenAuditStatusCallback
from app.settings import settings

ALLOWED_OPERATOR_ROLES = {"admin", "operator"}
ACTIVE_COMMAND_STATUSES = {"queued", "dispatched", "acknowledged", "executing"}
FINAL_COMMAND_STATUSES = {"success", "failed", "rejected"}
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"queued", "dispatched", "acknowledged", "executing", "success", "failed", "rejected"},
    "dispatched": {"dispatched", "acknowledged", "executing", "success", "failed", "rejected"},
    "acknowledged": {"acknowledged", "executing", "success", "failed", "rejected"},
    "executing": {"executing", "success", "failed", "rejected"},
    "success": {"success"},
    "failed": {"failed"},
    "rejected": {"rejected"},
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _normalize_operator_config() -> dict[str, dict[str, str]]:
    raw = (settings.siren_audit_operators_json or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SIREN_AUDIT_CONFIG_INVALID",
                "message": f"invalid siren_audit_operators_json: {exc.msg}",
            },
        ) from exc

    operators: dict[str, dict[str, str]] = {}
    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict):
                continue
            operator_id = str(item.get("id", "")).strip()
            role = str(item.get("role", "")).strip().lower()
            if not operator_id or role not in ALLOWED_OPERATOR_ROLES:
                continue
            operators[operator_id] = {
                "id": operator_id,
                "name": str(item.get("name", "")).strip() or operator_id,
                "role": role,
            }
        return operators

    if isinstance(parsed, dict):
        for operator_id, value in parsed.items():
            operator_id = str(operator_id).strip()
            if not operator_id:
                continue
            if isinstance(value, str):
                role = value.strip().lower()
                name = operator_id
            elif isinstance(value, dict):
                role = str(value.get("role", "")).strip().lower()
                name = str(value.get("name", "")).strip() or operator_id
            else:
                continue
            if role not in ALLOWED_OPERATOR_ROLES:
                continue
            operators[operator_id] = {"id": operator_id, "name": name, "role": role}
    return operators


def list_nodes(session: Session) -> list[dict[str, Any]]:
    now = _now()
    rows = session.execute(
        select(EdgeNode).where(EdgeNode.enabled.is_(True)).order_by(EdgeNode.node_id.asc())
    ).scalars().all()
    items: list[dict[str, Any]] = []
    for row in rows:
        node_status = status_for_node(age_seconds(row.last_seen_utc, now))
        items.append(
            {
                "nodeId": row.node_id,
                "name": row.name,
                "location": row.location,
                "availabilityStatus": row.availability_status or node_status,
                "lastSeenUtc": _iso(row.last_seen_utc),
                "eligible": node_status in {"fresh", "stale"},
            }
        )
    return items


def _node_status(node: EdgeNode, now: datetime) -> str:
    return status_for_node(age_seconds(node.last_seen_utc, now))


def resolve_target_node(session: Session, node_id: str) -> EdgeNode:
    node = session.get(EdgeNode, node_id)
    if node is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SIREN_NODE_NOT_FOUND", "message": f"node {node_id} tidak ditemukan"},
        )
    if not node.enabled:
        raise HTTPException(
            status_code=403,
            detail={"code": "SIREN_NODE_DISABLED", "message": f"node {node_id} sedang dinonaktifkan"},
        )
    current_status = _node_status(node, _now())
    if current_status not in {"fresh", "stale"}:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SIREN_NODE_NOT_ELIGIBLE",
                "message": f"node {node_id} belum siap menerima test sirine (status: {current_status})",
            },
        )
    return node


def _remaining_seconds(until: datetime | None, now: datetime | None = None) -> int:
    if until is None:
        return 0
    current = now or _now()
    return max(0, math.ceil((until - current).total_seconds()))


def ensure_no_active_cooldown(session: Session, node_id: str) -> None:
    now = _now()
    active = session.execute(
        select(SirenAuditRequest)
        .where(SirenAuditRequest.node_id == node_id)
        .where(SirenAuditRequest.cooldown_until > now)
        .order_by(SirenAuditRequest.cooldown_until.desc())
        .limit(1)
    ).scalars().first()
    if active is None:
        return
    remaining = _remaining_seconds(active.cooldown_until, now)
    raise HTTPException(
        status_code=409,
        detail={
            "code": "SIREN_COOLDOWN_ACTIVE",
            "message": f"test sirine untuk node {node_id} masih cooldown",
            "cooldownRemainingSeconds": remaining,
            "cooldownUntil": active.cooldown_until.isoformat(),
            "requestId": str(active.request_id),
        },
    )


def _serialize_request(row: SirenAuditRequest, now: datetime | None = None) -> dict[str, Any]:
    current = now or _now()
    return {
        "id": row.id,
        "requestId": str(row.request_id),
        "nodeId": row.node_id,
        "requestedBy": row.requested_by,
        "requestedRole": row.requested_role,
        "requestedAt": row.requested_at.isoformat(),
        "durationSec": row.duration_sec,
        "repeats": row.repeats,
        "gapSec": row.gap_sec,
        "reason": row.reason,
        "status": row.status,
        "resultMessage": row.result_message,
        "cooldownUntil": row.cooldown_until.isoformat(),
        "cooldownRemainingSeconds": _remaining_seconds(row.cooldown_until, current),
        "executedAt": _iso(row.executed_at),
        "updatedAt": row.updated_at_utc.isoformat(),
        "command": row.command_payload_json,
        "resultDetails": row.result_details_json,
    }


def _serialize_status_update(row: SirenAuditStatusUpdate) -> dict[str, Any]:
    return {
        "status": row.status,
        "message": row.message,
        "details": row.details_json,
        "reportedBy": row.reported_by,
        "reportedAt": row.reported_at_utc.isoformat(),
    }


def _build_command_payload(
    *,
    request_id: uuid.UUID,
    node_id: str,
    requested_by: str,
    requested_role: str,
    requested_at: datetime,
    duration_sec: float,
    repeats: int,
    gap_sec: float,
    reason: str,
) -> dict[str, Any]:
    return {
        "type": "siren_audit_test",
        "requestId": str(request_id),
        "nodeId": node_id,
        "parameters": {
            "durationSec": duration_sec,
            "repeats": repeats,
            "gapSec": gap_sec,
        },
        "requestedBy": requested_by,
        "requestedRole": requested_role,
        "requestedAt": requested_at.isoformat(),
        "reason": reason,
    }


def _append_status_update(
    session: Session,
    *,
    request_id: uuid.UUID,
    node_id: str,
    status: str,
    reported_at_utc: datetime,
    message: str | None,
    details: dict[str, Any] | None,
    reported_by: str | None,
) -> None:
    session.add(
        SirenAuditStatusUpdate(
            request_id=request_id,
            node_id=node_id,
            status=status,
            message=message,
            details_json=details,
            reported_by=reported_by,
            reported_at_utc=reported_at_utc,
        )
    )


def create_audit_request(
    session: Session,
    payload: SirenAuditRequestCreate,
    *,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    if actor_role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "SIREN_AUDIT_FORBIDDEN", "message": "admin role required"},
        )
    operator = {"id": actor_id, "name": actor_id, "role": actor_role}
    resolve_target_node(session, payload.node_id)
    ensure_no_active_cooldown(session, payload.node_id)

    now = _now()
    request_id = uuid.uuid4()
    cooldown_until = now + timedelta(seconds=settings.siren_audit_cooldown_seconds)
    command = _build_command_payload(
        request_id=request_id,
        node_id=payload.node_id,
        requested_by=operator["id"],
        requested_role=operator["role"],
        requested_at=now,
        duration_sec=payload.duration_sec,
        repeats=payload.repeats,
        gap_sec=payload.gap_sec,
        reason=payload.reason,
    )

    row = SirenAuditRequest(
        request_id=request_id,
        node_id=payload.node_id,
        requested_by=operator["id"],
        requested_role=operator["role"],
        requested_at=now,
        duration_sec=payload.duration_sec,
        repeats=payload.repeats,
        gap_sec=payload.gap_sec,
        reason=payload.reason,
        status="queued",
        cooldown_until=cooldown_until,
        command_payload_json=command,
        last_status_at_utc=now,
        updated_at_utc=now,
    )
    session.add(row)
    session.flush()
    _append_status_update(
        session,
        request_id=request_id,
        node_id=payload.node_id,
        status="queued",
        reported_at_utc=now,
        message="Permintaan test sirine diterima server dan masuk antrean command.",
        details=None,
        reported_by=operator["id"],
    )
    session.commit()
    session.refresh(row)
    result = _serialize_request(row, now)
    result["command"] = command
    return result


def get_latest_request(session: Session, node_id: str | None = None) -> dict[str, Any]:
    stmt = select(SirenAuditRequest).order_by(SirenAuditRequest.requested_at.desc()).limit(1)
    if node_id:
        stmt = stmt.where(SirenAuditRequest.node_id == node_id)
    latest = session.execute(stmt).scalars().first()
    if latest is None:
        return {"nodeId": node_id, "latest": None, "statusUpdates": []}
    updates = session.execute(
        select(SirenAuditStatusUpdate)
        .where(SirenAuditStatusUpdate.request_id == latest.request_id)
        .order_by(SirenAuditStatusUpdate.reported_at_utc.desc())
        .limit(20)
    ).scalars().all()
    return {
        "nodeId": latest.node_id,
        "latest": _serialize_request(latest),
        "statusUpdates": [_serialize_status_update(item) for item in updates],
    }


def list_history(
    session: Session,
    *,
    from_: str | None,
    to: str | None,
    node_id: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "1h")
    base = (
        select(SirenAuditRequest)
        .where(SirenAuditRequest.requested_at >= from_dt)
        .where(SirenAuditRequest.requested_at < to_dt)
    )
    count_stmt = (
        select(func.count())
        .select_from(SirenAuditRequest)
        .where(SirenAuditRequest.requested_at >= from_dt)
        .where(SirenAuditRequest.requested_at < to_dt)
    )
    if node_id:
        base = base.where(SirenAuditRequest.node_id == node_id)
        count_stmt = count_stmt.where(SirenAuditRequest.node_id == node_id)
    if status:
        base = base.where(SirenAuditRequest.status == status)
        count_stmt = count_stmt.where(SirenAuditRequest.status == status)

    total_items = int(session.execute(count_stmt).scalar() or 0)
    total_pages = max(1, math.ceil(total_items / page_size))
    current_page = min(page, total_pages)
    offset = (current_page - 1) * page_size

    rows = session.execute(
        base.order_by(SirenAuditRequest.requested_at.desc()).limit(page_size).offset(offset)
    ).scalars().all()

    return {
        "nodeId": node_id,
        "status": status,
        "fromUtc": from_dt.isoformat(),
        "toUtc": to_dt.isoformat(),
        "items": [_serialize_request(row) for row in rows],
        "meta": {
            "count": len(rows),
            "page": current_page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_prev": current_page > 1,
            "has_next": current_page < total_pages,
        },
    }


def get_options(session: Session, *, actor_id: str, actor_role: str) -> dict[str, Any]:
    configured = _normalize_operator_config().get(actor_id, {})
    return {
        "nodes": list_nodes(session),
        "operators": [
            {
                "id": actor_id,
                "name": configured.get("name", actor_id),
                "role": actor_role,
            }
        ],
        "limits": {
            "durationSec": {"min": 0.5, "max": 10},
            "repeats": {"min": 1, "max": 3},
            "gapSec": {"min": 0, "max": 10},
            "cooldownSeconds": settings.siren_audit_cooldown_seconds,
        },
        "auth": {
            "serverIdentityVerified": True,
            "clientRequestedByIgnored": True,
            "allowedRoles": ["admin"],
        },
    }


def get_pending_commands_for_node(session: Session, node: EdgeNode, limit: int = 1) -> dict[str, Any]:
    now = _now()
    rows = session.execute(
        select(SirenAuditRequest)
        .where(SirenAuditRequest.node_id == node.node_id)
        .where(SirenAuditRequest.status.in_(ACTIVE_COMMAND_STATUSES))
        .order_by(SirenAuditRequest.requested_at.asc())
        .limit(limit)
    ).scalars().all()

    items: list[dict[str, Any]] = []
    changed = False
    for row in rows:
        if row.status == "queued":
            row.status = "dispatched"
            row.updated_at_utc = now
            row.last_status_at_utc = now
            _append_status_update(
                session,
                request_id=row.request_id,
                node_id=row.node_id,
                status="dispatched",
                reported_at_utc=now,
                message="Command test sirine dikirim ke edge node untuk dieksekusi.",
                details=None,
                reported_by=node.node_id,
            )
            changed = True
        items.append(
            {
                "requestId": str(row.request_id),
                "nodeId": row.node_id,
                "status": row.status,
                "command": row.command_payload_json,
                "cooldownUntil": row.cooldown_until.isoformat(),
            }
        )
    if changed:
        session.commit()
    return {"nodeId": node.node_id, "items": items}


def apply_status_callback(session: Session, node: EdgeNode, payload: SirenAuditStatusCallback) -> dict[str, Any]:
    request_uuid = uuid.UUID(payload.request_id)
    row = session.execute(
        select(SirenAuditRequest).where(SirenAuditRequest.request_id == request_uuid)
    ).scalars().first()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SIREN_REQUEST_NOT_FOUND", "message": "request sirine tidak ditemukan"},
        )
    if row.node_id != node.node_id or payload.node_id != node.node_id:
        raise HTTPException(
            status_code=409,
            detail={"code": "SIREN_NODE_MISMATCH", "message": "node callback tidak cocok dengan request"},
        )
    if payload.status not in ALLOWED_TRANSITIONS.get(row.status, set()):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SIREN_STATUS_TRANSITION_INVALID",
                "message": f"transisi status {row.status} -> {payload.status} tidak diizinkan",
            },
        )

    status_time = payload.executed_at or _now()
    row.status = payload.status
    row.updated_at_utc = _now()
    row.last_status_at_utc = status_time
    if payload.message:
        row.result_message = payload.message
    if payload.details is not None:
        row.result_details_json = payload.details
    if payload.status in FINAL_COMMAND_STATUSES:
        row.executed_at = status_time
        final_cooldown = status_time + timedelta(seconds=settings.siren_audit_cooldown_seconds)
        if final_cooldown > row.cooldown_until:
            row.cooldown_until = final_cooldown

    _append_status_update(
        session,
        request_id=row.request_id,
        node_id=row.node_id,
        status=payload.status,
        reported_at_utc=status_time,
        message=payload.message,
        details=payload.details,
        reported_by=node.node_id,
    )
    session.commit()
    session.refresh(row)
    return {
        "requestId": str(row.request_id),
        "nodeId": row.node_id,
        "status": row.status,
        "executedAt": _iso(row.executed_at),
        "message": row.result_message,
        "cooldownUntil": row.cooldown_until.isoformat(),
        "cooldownRemainingSeconds": _remaining_seconds(row.cooldown_until),
    }
