"""Storage ports (protocols) for pluggable backends."""

from typing import Any, Protocol

from ascp.core.types import AuditEvent, AssuranceRunRecord, PolicyRef, RunId, TenantId


class PolicyRepository(Protocol):
    """Get policy by ref; list versions; optional put for API later."""

    def get_policy_document(self, ref: PolicyRef) -> dict[str, Any] | None:
        ...

    def list_policy_versions(self, tenant_id: TenantId, name: str = "default") -> list[PolicyRef]:
        ...

    def put_policy_document(self, ref: PolicyRef, document: dict[str, Any]) -> None:
        ...


class TrustRegistry(Protocol):
    """Register and check allowed model artifacts; scanner writes, gateway reads."""

    def register_model(
        self,
        tenant_id: TenantId,
        model_id: str,
        digest: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...

    def is_model_allowed(self, tenant_id: TenantId, model_id: str) -> bool:
        ...

    def list_models(self, tenant_id: TenantId) -> list[tuple[str, str | None]]:
        ...


class AuditSink(Protocol):
    """Append audit events; optional batch; can forward to OTLP/webhook."""

    def append(self, event: AuditEvent) -> None:
        ...

    def append_batch(self, events: list[AuditEvent]) -> None:
        ...


class ArtifactStore(Protocol):
    """Blob storage by key; metadata DB stores pointer only."""

    def put(self, key: str, data: bytes) -> str:
        """Returns storage key/uri."""
        ...

    def get(self, key: str) -> bytes | None:
        ...


class AssuranceRunStore(Protocol):
    """Persist red-team / eval run metadata and summary."""

    def create_run(self, tenant_id: TenantId, metadata: dict[str, Any] | None) -> RunId:
        ...

    def update_run(
        self,
        run_id: RunId,
        status: str,
        summary: dict[str, Any] | None = None,
    ) -> None:
        ...

    def get_run(self, run_id: RunId) -> AssuranceRunRecord | None:
        ...
