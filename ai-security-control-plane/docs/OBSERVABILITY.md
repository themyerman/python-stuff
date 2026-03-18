# Observability

## Audit trail

- Events are appended to the configured backend (SQLite/Postgres) as JSON rows.
- **Export:** `GET /v1/tenants/{tenant_id}/audit/export.jsonl?limit=5000&since=ISO8601` returns **NDJSON** (one `AuditEvent` per line). Filter is by `tenant_id` inside each event.
- **Webhook (async fire-and-forget):** set **`ASCP_AUDIT_WEBHOOK_URL`** to an HTTPS endpoint; each `append`/`append_batch` POSTs a JSON array of event payloads (`httpx`, 5s timeout). Failures are swallowed—use for best-effort SIEM forwarding, not as sole storage.

## Retention & redaction

- Retention is **not** enforced in-app; size-limit exports with `limit` and rotate DB/files at the ops layer.
- Do **not** log raw user prompts or upstream API keys in shared audit payloads; gateway audit entries store outcomes and metadata only.

## OTLP

- Native OTLP export is not wired yet. Use **webhook → your collector** or export **JSONL** into your pipeline.
