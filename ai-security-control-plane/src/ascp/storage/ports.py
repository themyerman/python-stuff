"""Storage port protocols — swap implementations without changing callers."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from ascp.core.types import AuditEvent, PolicyRef, RunId, TenantId, WorkspaceId


class AssuranceRunRecord(BaseModel):
    """Metadata for an assurance (test) run."""

    run_id: RunId
    tenant_id: TenantId
    workspace_id: WorkspaceId | None = None
    status: str = "created"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyRepository(Protocol):
    def get_policy_document(self, ref: PolicyRef) -> dict[str, Any] | None: ...

    def put_policy_document(self, ref: PolicyRef, document: dict[str, Any]) -> None: ...

    def list_policy_versions(self, tenant_id: TenantId, policy_id: str) -> list[PolicyRef]: ...


class TrustRegistry(Protocol):
    def register_model(self, tenant_id: TenantId, model_id: str, *, metadata: dict[str, Any] | None = None) -> None: ...

    def is_model_allowed(self, tenant_id: TenantId, model_id: str) -> bool: ...

    def list_models(self, tenant_id: TenantId) -> list[str]: ...


class AuditSink(Protocol):
    def append(self, event: AuditEvent) -> None: ...

    def append_batch(self, events: list[AuditEvent]) -> None: ...


class ArtifactStore(Protocol):
    def put_bytes(self, key: str, data: bytes) -> str: ...

    def get_bytes(self, key: str) -> bytes | None: ...


class AssuranceRunStore(Protocol):
    def create_run(self, record: AssuranceRunRecord) -> RunId: ...

    def update_run(
        self,
        run_id: RunId,
        *,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def get_run(self, run_id: RunId) -> AssuranceRunRecord | None: ...
