# Architecture (foundations)

High-level view of the **foundations layer**: ports, reference backend, and how later pillars (gateway, scanner, red-team, RAG lab) plug in.

## Ports (interfaces)

Core services depend on **storage and policy abstractions**, not concrete DBs or drivers.

### Storage (`ascp.storage.ports`)

| Port | Responsibility |
|------|----------------|
| **PolicyRepository** | Get policy document by `PolicyRef`; list versions; put (for API later). |
| **TrustRegistry** | Register allowed models (scanner writes); `is_model_allowed` (gateway reads). |
| **AuditSink** | `append(AuditEvent)` and `append_batch`; can forward to OTLP/webhook. |
| **ArtifactStore** | `put(key, bytes)` / `get(key)` for blobs (SBOM, traces); metadata DB stores pointer only. |
| **AssuranceRunStore** | `create_run`, `update_run`, `get_run` for red-team / scan / RAG eval runs. |

### Policy (`ascp.policy.engine`)

- **PolicyEngine** (protocol): `evaluate(ctx: PolicyEvaluationContext) -> Decision`.
- Stub implementations: **AllowAllPolicyEngine**, **TrustRegistryPolicyEngine** (deny if model not in registry).

## Reference backend

**SqliteFsBackend** (`ascp.storage.sqlite_fs`) implements all five storage ports:

- **SQLite** for policies, trust registry, audit_events, assurance_runs.
- **Local filesystem** directory for artifact blobs (key hashed for safe filenames).

Config: `database_url` (default `sqlite:///ascp.db`), `artifact_root` (default `ascp_artifacts`).

## Core types (`ascp.core.types`)

- **TenantId**, **WorkspaceId**, **RunId** — identifiers; v0 can use single tenant `"default"`.
- **PolicyRef** — immutable pointer (tenant, name, version).
- **Decision** / **DecisionOutcome** — allow / block / warn + reason_codes and violations.
- **AuditEvent** — event_type, tenant, policy_ref, correlation_id, outcome, payload_ref, metadata, occurred_at.
- **PolicyEvaluationContext** — input to policy engine (tenant, environment, model_id, tool_name, etc.).
- **AssuranceRunRecord** — run_id, tenant_id, status, summary, created_at.
- **new_correlation_id()**, **new_run_id()** — generate IDs; propagate correlation_id in logs and audit.

## Configuration and logging

- **Settings** (`ascp.config`): pydantic-settings with `ASCP_` prefix; `database_url`, `artifact_root`, `log_level`.
- **Logging** (`ascp.logging_utils`): `configure_logging(level)`, `get_logger(name)`, `bind_correlation_id(cid)`; filter adds `correlation_id` to each record.

## Extension points

- **New policy backend**: Implement `PolicyRepository`, `TrustRegistry`, etc.; wire same interfaces. Gateway and red-team call sites stay unchanged.
- **New policy engine**: Implement `PolicyEngine.evaluate(ctx) -> Decision`; use TrustRegistry or policy document when ready.
- **Audit forwarding**: Second implementation of `AuditSink` that appends to DB and forwards to Kafka/OTLP/webhook.

## What is out of scope (foundations)

- HTTP gateway (OpenAI-compatible proxy, etc.).
- Full policy DSL (YAML, OPA).
- Dashboard, GitHub Action, multi-tenant auth.

These consume the foundations once ports and types are stable.
