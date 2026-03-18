# AI Security Control Plane (ASCP)

**ASCP** is a Python **control plane** for teams shipping LLM-powered apps. It helps you **enforce policies** (which models and tools are allowed), **audit** decisions, **proxy** OpenAI-style chat traffic through those policies, and run **assurance** (red-team style) scenarios against a **staging endpoint**—with everything stored in a **pluggable** layer (today: **SQLite + local files**; designed so you can swap in Postgres, S3, etc.).

Longer product vision (four pillars: gateway, red-team, RAG lab, supply chain) is in **[prd.md](./prd.md)**. **Ports, backends, and internals** are in **[ARCHITECTURE.md](./ARCHITECTURE.md)**.

---

## What you get today

| Area | What it does |
|------|----------------|
| **Trust registry** | Per-tenant allowlist of **model IDs**. Unregistered models can be blocked. |
| **Policy documents (v1)** | JSON/YAML rules for **tools**: allowlist / denylist, block vs warn on violations. See [examples/policy.example.yaml](./examples/policy.example.yaml). |
| **Evaluation** | Chain: trust registry → document policy. Used by the API **evaluate** endpoint and the **gateway**. |
| **Operator HTTP API** | Policies, models, **evaluate**, **assurance runs**, **OpenAI-compatible gateway proxy**. |
| **Gateway** | `POST .../gateway/v1/chat/completions` — policy check, then **sync** or **`stream: true`** (SSE) forward to **`ASCP_UPSTREAM_*`**. |
| **Assurance runs** | **`builtin-v0`**; stub or live **`target_url`**. **Scoring:** pass rate, jailbreak/refusal + leak heuristics; **`min_pass_rate`** in run metadata (default 0.7). **`?fail_ci=true`** on execute → **422** if below threshold. **`replay_from_run_id`** copies target settings into a new run. |
| **Docker** | **`docker compose up --build`** (SQLite volume). Profile **`postgres`**: Postgres + API on port **8001** (`pip install ".[postgres]"` in image for PG URL). |
| **Postgres** | Set **`ASCP_DATABASE_URL=postgresql://...`** and **`pip install ".[postgres]"`** — same API, metadata in Postgres, artifacts still on disk. |
| **Tenant API keys** | **`POST /v1/admin/tenants/{id}/api-keys`** (needs **`ASCP_API_KEY`**) returns a one-time **`ascp_ten_...`** token. Use **Bearer** or **`X-ASCP-Tenant-Token`**; path tenant must match key’s tenant. |
| **Supply chain (stub)** | Upload lockfile: **`POST .../supply-chain/lockfile?filename=...`** (raw body) → SHA-256 + artifact. **`POST .../supply-chain/cyclonedx`** stores CycloneDX JSON blob. |
| **RAG lab (stub)** | **`PUT .../rag/corpora/{corpus_id}`** with **`chunks: [{chunk_id, text, is_poison}]`**. **`POST .../rag/corpora/{id}/evaluate`** keyword overlap “retrieval” + **`poison_in_top_k`**. |
| **Observability** | **`GET .../audit/export.jsonl`** (tenant-filtered NDJSON). Optional **`ASCP_AUDIT_WEBHOOK_URL`** POST on each audit append. See **[docs/OBSERVABILITY.md](./docs/OBSERVABILITY.md)**. |

**Roadmap:** S3 artifacts, full SBOM diffing, richer RAG/vector eval, hosted UI, OTLP native export.

---

## Requirements

- **Python 3.11+**

---

## Install

**Library only** (policy types, engines, SQLite backend, YAML policies, assurance runner—usable from your own code):

```bash
pip install -e .          # from repo root, after clone
# or eventually: pip install ascp
```

**Operator API + gateway** (FastAPI + Uvicorn):

```bash
pip install -e ".[api]"
# Postgres metadata: pip install -e ".[api,postgres]"
# dev/tests: pip install -e ".[dev]"
```

---

## Run the API server

```bash
export ASCP_DATABASE_URL="sqlite:///./ascp.db"
export ASCP_ARTIFACT_ROOT="./ascp_artifacts"
# Gateway: forward allowed traffic to OpenAI-compatible API
export ASCP_UPSTREAM_BASE_URL="https://api.openai.com/v1"
export ASCP_UPSTREAM_API_KEY="sk-..."   # upstream provider key (keep secret)

# Optional: lock down the operator API (health check stays open)
# export ASCP_API_KEY="your-operator-secret"

ascp-serve
# Listens on 0.0.0.0:8000 by default
```

**Docker**

```bash
docker compose up --build
# Data under volume ./ascp-data (mapped in compose). Postgres profile: docker compose --profile postgres up --build
```

Configuration uses **`ASCP_*`** environment variables (and optional `.env`). See **`ascp.config.Settings`** for the full list (timeouts, assurance target auth, log level, etc.).

---

## Using it (quick flows)

Replace `TENANT`, `HOST` (e.g. `http://127.0.0.1:8000`), and add headers if **`ASCP_API_KEY`** is set:

`Authorization: Bearer <key>` or `X-ASCP-API-Key: <key>`.

### 1. Register a model and install a policy

```bash
# Policy document (tools: allowlist example)
curl -X PUT "$HOST/v1/tenants/$TENANT/policies/default/versions/v1" \
  -H "Content-Type: application/json" \
  -d '{"schema_version":"1","tools":{"mode":"allowlist","allowed":["search","read_file"],"deny":["execute_shell"],"on_violation":"block"}}'

curl -X POST "$HOST/v1/tenants/$TENANT/models" \
  -H "Content-Type: application/json" \
  -d '{"model_id":"gpt-4o"}'
```

### 2. Evaluate a decision (no LLM call)

```bash
curl -X POST "$HOST/v1/tenants/$TENANT/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"policy_id":"default","policy_version":"v1","model_id":"gpt-4o","tools_invoked":["search"],"audit":true}'
```

### 3. Chat via the gateway (policy → upstream)

Point your app at ASCP instead of the provider directly:

`POST $HOST/v1/tenants/$TENANT/gateway/v1/chat/completions?policy_id=default&policy_version=v1`

Same JSON body as OpenAI **chat completions** (must include **`model`**). Blocked requests return **403** with violation details.

### 4. Assurance run (stub vs live)

```bash
# List suites
curl "$HOST/v1/assurance/suites"

# Stub run (no HTTP to a target)
curl -X POST "$HOST/v1/tenants/$TENANT/assurance-runs" \
  -H "Content-Type: application/json" \
  -d '{"suite":"builtin-v0"}'
# → run_id; then:
curl -X POST "$HOST/v1/tenants/$TENANT/assurance-runs/<run_id>/execute"

# Live run: POST each scenario to your staging chat URL
curl -X POST "$HOST/v1/tenants/$TENANT/assurance-runs" \
  -H "Content-Type: application/json" \
  -d '{"suite":"builtin-v0","metadata":{"target_url":"https://your-staging.example/v1/chat/completions","target_model":"gpt-4o-mini"}}'
# Optional: ASCP_ASSURANCE_TARGET_AUTHORIZATION on server for Bearer to staging
curl -X POST "$HOST/v1/tenants/$TENANT/assurance-runs/<run_id>/execute"
```

Reports land under artifact keys like **`assurance/<run_id>/report.json`** (on disk under **`ASCP_ARTIFACT_ROOT`**).

---

## Python library (skipping HTTP)

```python
from ascp import SqliteFsBackend, PolicyRef, PolicyEvaluationContext
from ascp.policy import ChainedPolicyEngine, TrustRegistryPolicyEngine, DocumentPolicyEngine

backend = SqliteFsBackend("sqlite:///./ascp.db", artifact_root="./ascp_artifacts")
backend.register_model("my-tenant", "gpt-4o")
backend.put_policy_document(
    PolicyRef(tenant_id="my-tenant", policy_id="default", version="v1"),
    {"schema_version": "1", "tools": {"mode": "open"}},
)
chain = ChainedPolicyEngine(
    TrustRegistryPolicyEngine(backend),
    DocumentPolicyEngine(backend, policy_ref=PolicyRef(tenant_id="my-tenant", policy_id="default", version="v1")),
)
decision = chain.evaluate(
    PolicyEvaluationContext(tenant_id="my-tenant", model_id="gpt-4o", extra={"tools_invoked": ["search"]})
)
print(decision.outcome, decision.violations)
```

---

## Tests

```bash
pip install -e ".[dev]"
PYTHONPATH=src python -m pytest tests/ -q
```

---

## Admin & tenant tokens

With **`ASCP_API_KEY`** set, use it as **Bearer** for all routes, **or** create per-tenant keys:

```bash
curl -X POST "$HOST/v1/admin/tenants/$TENANT/api-keys" \
  -H "Authorization: Bearer $ASCP_API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"ci"}'
# Save the returned "token"; then:
curl "$HOST/v1/tenants/$TENANT/models" -H "Authorization: Bearer ascp_ten_...."
```

## Roadmap (abbrev.)

- S3/GCS artifacts; vector RAG eval; OTLP; Helm; responsible-use docs for offensive scenarios. See **[prd.md](./prd.md)**.

---

## License

MIT (see [pyproject.toml](./pyproject.toml)).
