# ASCP architecture — ports and reference backend

## Ports (`ascp.storage.ports`)

Storage and side effects are defined as **`typing.Protocol`** interfaces so production can swap Postgres, S3, Kafka, etc. without changing policy or gateway code.

| Port | Role |
|------|------|
| **PolicyRepository** | Versioned policy documents as `dict` (JSON-serializable). `get_policy_document`, `put_policy_document`, `list_policy_versions`. |
| **TrustRegistry** | Tenant-scoped model allowlist. `register_model`, `is_model_allowed`, `list_models`. |
| **AuditSink** | Append-only audit trail. `append`, `append_batch` with `AuditEvent`. |
| **ArtifactStore** | Binary blobs (reports, captures). `put_bytes`, `get_bytes` keyed by path-like string. |
| **AssuranceRunStore** | Assurance run metadata via `AssuranceRunRecord`. `create_run`, `update_run`, `get_run`, `list_runs(tenant_id, limit=...)`. |

## Reference backend: `SqliteFsBackend` (`ascp.storage.sqlite_fs`)

Single class implementing **all** ports above:

- **SQLite** (`database_url`, e.g. `sqlite:///./ascp.db`) with tables:
  - `policies` — tenant, policy_id, version, JSON document
  - `trust_registry` — tenant, model_id, metadata JSON
  - `audit_events` — full `AuditEvent` JSON per row
  - `assurance_runs` — run metadata + status + JSON metadata
- **Filesystem** under **`artifact_root`**: one file per artifact key (safe relative paths only).

Use this for local dev, tests, and small deployments; scale-out paths replace individual ports with cloud-native implementations.

## Policy engines (`ascp.policy.engine`, `ascp.policy.document_engine`)

- **`PolicyEngine`**: `evaluate(PolicyEvaluationContext) -> Decision`.
- **`AllowAllPolicyEngine`**: always `ALLOW`.
- **`TrustRegistryPolicyEngine`**: when `require_registration=True`, blocks with `TRUST_MODEL_NOT_ALLOWED` if `model_id` is present and not in the tenant’s trust registry.
- **`DocumentPolicyEngine`**: loads **`PolicyDocumentV1`** from `PolicyRepository` for a fixed `PolicyRef`; enforces **tools** (`mode`: `open` | `allowlist`, `allowed`, `deny`, `on_violation`: `block` | `warn`). Context: `extra["tools_invoked"]` or `extra["tools"]`.
- **`ChainedPolicyEngine`**: runs multiple engines; first `BLOCK` wins; else aggregates `WARN`.

## Policy documents v1 (`ascp.policy.document`)

YAML/JSON mapping validated by Pydantic; **`policy_document_from_yaml(text)`**. Stored like any policy document via `PolicyRepository`.

## Operator API (`ascp.api`)

FastAPI: health, policy CRUD by version, model registration, **`POST .../evaluate`** (chain: trust + document), assurance run lifecycle + **`POST .../assurance-runs/{id}/execute`** (stub), **`GET /v1/assurance/suites`**. If **`ASCP_API_KEY`** is set, all routes except **`GET /health`** require the key. **`pip install 'ascp[api]'`**, **`ascp-serve`**.

## Assurance (`ascp.assurance`)

Versioned scenario suites (e.g. **`builtin-v0`**). **`execute_builtin_stub_run`** updates **`AssuranceRunStore`**, writes JSON report to **`ArtifactStore`** under **`assurance/{run_id}/report.json`**, appends **`ASSURANCE_RUN`** audit when a sink is provided.

## Core types (`ascp.core.types`)

IDs, `PolicyRef`, `Decision` / `Violation`, `AuditEvent`, and `PolicyEvaluationContext` are Pydantic models shared across ports and engines.
