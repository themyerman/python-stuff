"""Core domain types."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

TenantId = str
WorkspaceId = str
RunId = str


def new_run_id() -> RunId:
    return str(uuid.uuid4())


def new_correlation_id() -> str:
    return str(uuid.uuid4())


class PolicyRef(BaseModel):
    model_config = {"frozen": True}
    tenant_id: TenantId = "default"
    name: str = "default"
    version: str = "1"

    def key(self) -> str:
        return f"{self.tenant_id}:{self.name}@{self.version}"


class DecisionOutcome(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    WARN = "warn"


class Violation(BaseModel):
    code: str
    message: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)


class Decision(BaseModel):
    outcome: DecisionOutcome
    reason_codes: list[str] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)


class AuditEventType(str, Enum):
    POLICY_EVALUATION = "policy_evaluation"
    GATEWAY_REQUEST = "gateway_request"
    TOOL_INVOCATION = "tool_invocation"
    SCAN_COMPLETED = "scan_completed"
    ASSURANCE_RUN = "assurance_run"
    GENERIC = "generic"


class AuditEvent(BaseModel):
    event_type: AuditEventType
    tenant_id: TenantId = "default"
    policy_ref: PolicyRef | None = None
    correlation_id: str | None = None
    outcome: DecisionOutcome | None = None
    payload_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AssuranceRunRecord(BaseModel):
    """Read-only run record for assurance (red-team, scan, RAG eval)."""

    run_id: RunId
    tenant_id: TenantId
    status: str
    summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PolicyEvaluationContext(BaseModel):
    tenant_id: TenantId = "default"
    workspace_id: WorkspaceId | None = None
    environment: str = "prod"
    model_id: str | None = None
    tool_name: str | None = None
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    policy_ref: PolicyRef | None = None
