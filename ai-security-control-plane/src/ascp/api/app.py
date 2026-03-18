"""FastAPI operator API: policies, trust registry, evaluate, assurance runs."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ascp.assurance import execute_builtin_stub_run, list_suite_ids
from ascp.config import Settings
from ascp.core.types import (
    AuditEvent,
    AuditEventType,
    PolicyEvaluationContext,
    PolicyRef,
    new_run_id,
)
from ascp.policy import (
    ChainedPolicyEngine,
    DocumentPolicyEngine,
    TrustRegistryPolicyEngine,
)
from ascp.storage import AssuranceRunRecord, SqliteFsBackend


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


class CreateAssuranceRunBody(BaseModel):
    suite: str = "builtin-v0"
    workspace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PatchAssuranceRunBody(BaseModel):
    status: str | None = None
    metadata: dict[str, Any] | None = None


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
        description="AI Security Control Plane — policies, trust registry, evaluation, assurance",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next):
        key = getattr(request.app.state, "settings", None)
        api_key = getattr(key, "api_key", None) if key else None
        if not api_key:
            return await call_next(request)
        path = request.url.path.rstrip("/") or "/"
        if path == "/health":
            return await call_next(request)
        auth = request.headers.get("authorization") or ""
        header_key = request.headers.get("x-ascp-api-key")
        token = header_key
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        if not token or token != api_key:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)

    def backend(request: Request) -> SqliteFsBackend:
        return request.app.state.backend

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/assurance/suites")
    def assurance_suites() -> dict[str, list[str]]:
        return {"suites": list_suite_ids()}

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

    @app.post("/v1/tenants/{tenant_id}/assurance-runs")
    def create_assurance_run(
        tenant_id: str,
        body: CreateAssuranceRunBody,
        request: Request,
    ) -> dict[str, str]:
        b = backend(request)
        rid = new_run_id()
        meta = {**body.metadata, "suite": body.suite}
        rec = AssuranceRunRecord(
            run_id=rid,
            tenant_id=tenant_id,
            workspace_id=body.workspace_id,
            status="created",
            metadata=meta,
        )
        b.create_run(rec)
        return {"run_id": rid}

    @app.get("/v1/tenants/{tenant_id}/assurance-runs")
    def list_assurance_runs(
        tenant_id: str,
        request: Request,
        limit: int = 50,
    ) -> dict[str, Any]:
        b = backend(request)
        runs = b.list_runs(tenant_id, limit=limit)
        return {"runs": [r.model_dump() for r in runs]}

    @app.get("/v1/tenants/{tenant_id}/assurance-runs/{run_id}")
    def get_assurance_run(
        tenant_id: str,
        run_id: str,
        request: Request,
    ) -> dict[str, Any]:
        b = backend(request)
        rec = b.get_run(run_id)
        if rec is None or rec.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="run not found")
        return rec.model_dump()

    @app.patch("/v1/tenants/{tenant_id}/assurance-runs/{run_id}")
    def patch_assurance_run(
        tenant_id: str,
        run_id: str,
        body: PatchAssuranceRunBody,
        request: Request,
    ) -> dict[str, Any]:
        b = backend(request)
        rec = b.get_run(run_id)
        if rec is None or rec.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="run not found")
        try:
            b.update_run(
                run_id,
                status=body.status,
                metadata=body.metadata,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found") from None
        out = b.get_run(run_id)
        assert out is not None
        return out.model_dump()

    @app.post("/v1/tenants/{tenant_id}/assurance-runs/{run_id}/execute")
    def execute_assurance_run(
        tenant_id: str,
        run_id: str,
        request: Request,
    ) -> dict[str, Any]:
        b = backend(request)
        try:
            return execute_builtin_stub_run(
                runs=b,
                artifacts=b,
                audit=b,
                tenant_id=tenant_id,
                run_id=run_id,
            )
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                raise HTTPException(status_code=404, detail=msg) from e
            raise HTTPException(status_code=400, detail=msg) from e

    return app


app = create_app()
