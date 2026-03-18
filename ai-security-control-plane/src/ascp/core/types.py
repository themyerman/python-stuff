"""Core domain types: IDs, policy references, decisions, audit, evaluation context."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# --- Type aliases ---
TenantId = str
WorkspaceId = str
RunId = str


def new_run_id() -> RunId:
    return str(uuid.uuid4())


def new_correlation_id() -> str:
    return str(uuid.uuid4())


class PolicyRef(BaseModel):
    """Immutable reference to a versioned policy document."""

    model_config = {"frozen": True}

    tenant_id: TenantId
    policy_id: str
    version: str


class DecisionOutcome(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    WARN = "WARN"


class Violation(BaseModel):
    code: str
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)


class Decision(BaseModel):
    outcome: DecisionOutcome
    violations: list[Violation] = Field(default_factory=list)
    correlation_id: str | None = None


class AuditEventType(str, Enum):
    POLICY_EVALUATION = "POLICY_EVALUATION"
    GATEWAY_REQUEST = "GATEWAY_REQUEST"
    ASSURANCE_RUN = "ASSURANCE_RUN"
    TRUST_CHANGE = "TRUST_CHANGE"
    SYSTEM = "SYSTEM"


class AuditEvent(BaseModel):
    event_type: AuditEventType
    tenant_id: TenantId
    correlation_id: str | None = None
    workspace_id: WorkspaceId | None = None
    run_id: RunId | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PolicyEvaluationContext(BaseModel):
    """Inputs passed to a policy engine for one evaluation."""

    tenant_id: TenantId
    workspace_id: WorkspaceId | None = None
    run_id: RunId | None = None
    model_id: str | None = None
    correlation_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
