from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

SirenAuditLifecycleStatus = Literal[
    "queued",
    "dispatched",
    "acknowledged",
    "executing",
    "success",
    "failed",
    "rejected",
]
OperatorRole = Literal["admin", "operator"]


class SirenAuditRequestCreate(BaseModel):
    node_id: str = Field(alias="nodeId", min_length=1)
    requested_by: str = Field(alias="requestedBy", min_length=1)
    duration_sec: float = Field(alias="durationSec", ge=0.5, le=10)
    repeats: int = Field(ge=1, le=3)
    gap_sec: float = Field(alias="gapSec", ge=0, le=10)
    reason: str = Field(min_length=1)

    @field_validator("node_id", "requested_by", "reason")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field is required")
        return stripped


class SirenAuditParameters(BaseModel):
    durationSec: float
    repeats: int
    gapSec: float


class SirenAuditCommandPayload(BaseModel):
    type: Literal["siren_audit_test"] = "siren_audit_test"
    requestId: str
    nodeId: str
    parameters: SirenAuditParameters
    requestedBy: str
    requestedRole: OperatorRole
    requestedAt: str
    reason: str


class SirenAuditCreateResponse(BaseModel):
    id: int
    requestId: str
    nodeId: str
    requestedBy: str
    requestedRole: OperatorRole
    requestedAt: str
    durationSec: float
    repeats: int
    gapSec: float
    reason: str
    status: SirenAuditLifecycleStatus
    resultMessage: Optional[str] = None
    cooldownUntil: str
    cooldownRemainingSeconds: int
    command: SirenAuditCommandPayload


class SirenAuditStatusCallback(BaseModel):
    request_id: str = Field(alias="requestId", min_length=1)
    node_id: str = Field(alias="nodeId", min_length=1)
    status: SirenAuditLifecycleStatus
    executed_at: Optional[datetime] = Field(default=None, alias="executedAt")
    message: Optional[str] = None
    details: Optional[dict[str, Any]] = None

    @field_validator("request_id", "node_id")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field is required")
        return stripped


class SirenAuditStatusUpdateResponse(BaseModel):
    requestId: str
    nodeId: str
    status: SirenAuditLifecycleStatus
    executedAt: Optional[str] = None
    message: Optional[str] = None
    cooldownUntil: str
    cooldownRemainingSeconds: int


class SirenAuditHistoryItem(BaseModel):
    id: int
    requestId: str
    nodeId: str
    requestedBy: str
    requestedRole: OperatorRole
    requestedAt: str
    durationSec: float
    repeats: int
    gapSec: float
    reason: str
    status: SirenAuditLifecycleStatus
    resultMessage: Optional[str] = None
    cooldownUntil: str
    cooldownRemainingSeconds: int
    executedAt: Optional[str] = None
    updatedAt: str
    command: Optional[dict[str, Any]] = None
    resultDetails: Optional[dict[str, Any]] = None


class SirenAuditStatusUpdateItem(BaseModel):
    status: SirenAuditLifecycleStatus
    message: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    reportedBy: Optional[str] = None
    reportedAt: str


class SirenAuditLatestResponse(BaseModel):
    nodeId: Optional[str]
    latest: Optional[SirenAuditHistoryItem] = None
    statusUpdates: list[SirenAuditStatusUpdateItem] = []


class SirenAuditHistoryResponse(BaseModel):
    nodeId: Optional[str]
    status: Optional[str]
    fromUtc: str
    toUtc: str
    items: list[SirenAuditHistoryItem]
    meta: dict[str, Any]


class SirenAuditNodeOption(BaseModel):
    nodeId: str
    name: Optional[str] = None
    location: Optional[str] = None
    availabilityStatus: Optional[str] = None
    lastSeenUtc: Optional[str] = None
    eligible: bool


class SirenAuditOperatorOption(BaseModel):
    id: str
    name: Optional[str] = None
    role: OperatorRole


class SirenAuditOptionsResponse(BaseModel):
    nodes: list[SirenAuditNodeOption]
    operators: list[SirenAuditOperatorOption]
    limits: dict[str, Any]
    auth: dict[str, Any]


class SirenAuditPendingCommandItem(BaseModel):
    requestId: str
    nodeId: str
    status: SirenAuditLifecycleStatus
    command: SirenAuditCommandPayload
    cooldownUntil: str


class SirenAuditPendingCommandsResponse(BaseModel):
    nodeId: str
    items: list[SirenAuditPendingCommandItem]
