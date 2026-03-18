"""FastAPI operator API: policies, trust registry, evaluate."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from ascp.config import Settings
from ascp.core.types import (
    AuditEvent,
    AuditEventType,
    PolicyEvaluationContext,
    PolicyRef,
)
from ascp.policy import (
    ChainedPolicyEngine,
    DocumentPolicyEngine,
    TrustRegistryPolicyEngine,
)
from ascp.storage import SqliteFsBackend


class EvaluateBody(BaseModel):
    policy_id: str = "default"
    policy_version: str = "v1"
    model_id: str | None = None
    tools_invoked: list[str] = Field(default_factory=list)
    workspace_id: str | None = None
    audit: bool = True


class RegisterModelBody(BaseModel):
    model_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        backend = SqliteFsBackend(settings.database_url, settings.artifact_root)
        app.state.backend = backend
        app.state.settings = settings
        yield

    app = FastAPI(
        title="ASCP Operator API",
        description="AI Security Control Plane — policies, trust registry, evaluation",
        lifespan=lifespan,
    )

    def backend(request: Request) -> SqliteFsBackend:
        return request.app.state.backend

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.put(
        "/v1/tenants/{tenant_id}/policies/{policy_id}/versions/{version}",
        status_code=204,
    )
    def put_policy(
        tenant_id: str,
        policy_id: str,
        version: str,
        document: dict[str, Any],
        request: Request,
    ) -> None:
        b = backend(request)
        ref = PolicyRef(tenant_id=tenant_id, policy_id=policy_id, version=version)
        b.put_policy_document(ref, document)

    @app.get("/v1/tenants/{tenant_id}/policies/{policy_id}/versions/{version}")
    def get_policy(
        tenant_id: str,
        policy_id: str,
        version: str,
        request: Request,
    ) -> dict[str, Any] | None:
        b = backend(request)
        ref = PolicyRef(tenant_id=tenant_id, policy_id=policy_id, version=version)
        doc = b.get_policy_document(ref)
        if doc is None:
            raise HTTPException(status_code=404, detail="policy version not found")
        return doc

    @app.post("/v1/tenants/{tenant_id}/models", status_code=204)
    def register_model(
        tenant_id: str,
        body: RegisterModelBody,
        request: Request,
    ) -> None:
        b = backend(request)
        b.register_model(tenant_id, body.model_id, metadata=body.metadata or None)

    @app.get("/v1/tenants/{tenant_id}/models")
    def list_models(tenant_id: str, request: Request) -> dict[str, list[str]]:
        b = backend(request)
        return {"models": b.list_models(tenant_id)}

    @app.post("/v1/tenants/{tenant_id}/evaluate")
    def evaluate(
        tenant_id: str,
        body: EvaluateBody,
        request: Request,
    ) -> dict[str, Any]:
        b = backend(request)
        ref = PolicyRef(
            tenant_id=tenant_id,
            policy_id=body.policy_id,
            version=body.policy_version,
        )
        chain = ChainedPolicyEngine(
            TrustRegistryPolicyEngine(b, require_registration=True),
            DocumentPolicyEngine(b, policy_ref=ref),
        )
        extra: dict[str, Any] = {}
        if body.tools_invoked:
            extra["tools_invoked"] = body.tools_invoked
        ctx = PolicyEvaluationContext(
            tenant_id=tenant_id,
            workspace_id=body.workspace_id,
            model_id=body.model_id,
            extra=extra,
        )
        decision = chain.evaluate(ctx)

        if body.audit:
            b.append(
                AuditEvent(
                    event_type=AuditEventType.POLICY_EVALUATION,
                    tenant_id=tenant_id,
                    workspace_id=body.workspace_id,
                    correlation_id=decision.correlation_id,
                    payload={
                        "outcome": decision.outcome.value,
                        "violations": [v.model_dump() for v in decision.violations],
                        "policy_id": body.policy_id,
                        "policy_version": body.policy_version,
                        "model_id": body.model_id,
                        "tools_invoked": body.tools_invoked,
                    },
                )
            )

        return {
            "outcome": decision.outcome.value,
            "violations": [v.model_dump() for v in decision.violations],
            "correlation_id": decision.correlation_id,
        }

    return app


app = create_app()
