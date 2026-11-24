from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.ingest.auth import verify_node_token
from app.models.registry import EdgeNode
from app.query.auth import (
    AccessPrincipal,
    require_siren_enabled,
    verify_admin_user,
)
from app.schemas.siren import (
    SirenAuditCreateResponse,
    SirenAuditHistoryResponse,
    SirenAuditLatestResponse,
    SirenAuditOptionsResponse,
    SirenAuditPendingCommandsResponse,
    SirenAuditRequestCreate,
    SirenAuditStatusCallback,
    SirenAuditStatusUpdateResponse,
)
from app.services.siren_audit import (
    apply_status_callback,
    create_audit_request,
    get_latest_request,
    get_options,
    get_pending_commands_for_node,
    list_history,
)

router = APIRouter(prefix="/api/siren", tags=["siren"])
SirenEnabled = Annotated[None, Depends(require_siren_enabled)]
AdminPrincipal = Annotated[AccessPrincipal, Depends(verify_admin_user)]


@router.get("/audit-test/options", response_model=SirenAuditOptionsResponse)
def siren_audit_options(
    _enabled: SirenEnabled,
    principal: AdminPrincipal,
    session: Session = Depends(get_session),
) -> SirenAuditOptionsResponse:
    return SirenAuditOptionsResponse.model_validate(
        get_options(session, actor_id=principal.subject, actor_role=principal.role)
    )


@router.get("/audit-test/latest", response_model=SirenAuditLatestResponse)
def siren_audit_latest(
    _enabled: SirenEnabled,
    _principal: AdminPrincipal,
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> SirenAuditLatestResponse:
    return SirenAuditLatestResponse.model_validate(get_latest_request(session, node))


@router.get("/audit-test/history", response_model=SirenAuditHistoryResponse)
def siren_audit_history(
    _enabled: SirenEnabled,
    _principal: AdminPrincipal,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> SirenAuditHistoryResponse:
    return SirenAuditHistoryResponse.model_validate(
        list_history(
            session,
            from_=from_,
            to=to,
            node_id=node,
            status=status,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/audit-test", response_model=SirenAuditCreateResponse)
def create_siren_audit_test(
    body: SirenAuditRequestCreate,
    _enabled: SirenEnabled,
    principal: AdminPrincipal,
    session: Session = Depends(get_session),
) -> SirenAuditCreateResponse:
    return SirenAuditCreateResponse.model_validate(
        create_audit_request(
            session,
            body,
            actor_id=principal.subject,
            actor_role=principal.role,
        )
    )


@router.get(
    "/commands/pending",
    response_model=SirenAuditPendingCommandsResponse,
    include_in_schema=False,
)
def get_pending_siren_commands(
    _enabled: SirenEnabled,
    node: Annotated[EdgeNode, Depends(verify_node_token)],
    session: Session = Depends(get_session),
    limit: int = Query(default=1, ge=1, le=5),
) -> SirenAuditPendingCommandsResponse:
    return SirenAuditPendingCommandsResponse.model_validate(
        get_pending_commands_for_node(session, node=node, limit=limit)
    )


@router.post(
    "/audit-test/status",
    response_model=SirenAuditStatusUpdateResponse,
    include_in_schema=False,
)
def update_siren_audit_status(
    body: SirenAuditStatusCallback,
    _enabled: SirenEnabled,
    node: Annotated[EdgeNode, Depends(verify_node_token)],
    session: Session = Depends(get_session),
) -> SirenAuditStatusUpdateResponse:
    return SirenAuditStatusUpdateResponse.model_validate(
        apply_status_callback(session, node=node, payload=body)
    )
