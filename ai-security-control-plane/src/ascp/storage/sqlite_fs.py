"""SQLite + filesystem reference backend for all storage ports."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from ascp.core.types import (
    AuditEvent,
    AuditEventType,
    AssuranceRunRecord,
    PolicyRef,
    RunId,
    TenantId,
    new_run_id,
)
from ascp.storage.ports import (
    ArtifactStore,
    AssuranceRunStore,
    AuditSink,
    PolicyRepository,
    TrustRegistry,
)


def _safe_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:32]


class SqliteFsBackend(
    PolicyRepository, TrustRegistry, AuditSink, ArtifactStore, AssuranceRunStore
):
    """Single backend: SQLite for structured data, filesystem dir for blobs."""

    def __init__(self, database_url: str = "sqlite:///ascp.db", artifact_root: str = "ascp_artifacts"):
        path = database_url.replace("sqlite:///", "")
        self._db_path = path
        self._artifact_root = Path(artifact_root)
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS policies (
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, name, version)
                );
                CREATE TABLE IF NOT EXISTS trust_registry (
                    tenant_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    digest TEXT,
                    meta TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, model_id)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    policy_key TEXT,
                    correlation_id TEXT,
                    outcome TEXT,
                    payload_ref TEXT,
                    metadata TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS assurance_runs (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    # PolicyRepository
    def get_policy_document(self, ref: PolicyRef) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT body FROM policies WHERE tenant_id=? AND name=? AND version=?",
                (ref.tenant_id, ref.name, ref.version),
            ).fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def list_policy_versions(self, tenant_id: TenantId, name: str = "default") -> list[PolicyRef]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT tenant_id, name, version FROM policies WHERE tenant_id=? AND name=? ORDER BY version",
                (tenant_id, name),
            ).fetchall()
        return [PolicyRef(tenant_id=r[0], name=r[1], version=r[2]) for r in rows]

    def put_policy_document(self, ref: PolicyRef, document: dict[str, Any]) -> None:
        from datetime import datetime, timezone
        body = json.dumps(document)
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO policies (tenant_id, name, version, body, created_at) VALUES (?,?,?,?,?)",
                (ref.tenant_id, ref.name, ref.version, body, now),
            )

    # TrustRegistry
    def register_model(
        self,
        tenant_id: TenantId,
        model_id: str,
        digest: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        from datetime import datetime, timezone
        meta = json.dumps(metadata or {})
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO trust_registry (tenant_id, model_id, digest, meta, created_at) VALUES (?,?,?,?,?)",
                (tenant_id, model_id, digest, meta, now),
            )

    def is_model_allowed(self, tenant_id: TenantId, model_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM trust_registry WHERE tenant_id=? AND model_id=?",
                (tenant_id, model_id),
            ).fetchone()
        return row is not None

    def list_models(self, tenant_id: TenantId) -> list[tuple[str, str | None]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT model_id, digest FROM trust_registry WHERE tenant_id=?",
                (tenant_id,),
            ).fetchall()
        return [(r[0], r[1]) for r in rows]

    # AuditSink
    def append(self, event: AuditEvent) -> None:
        self.append_batch([event])

    def append_batch(self, events: list[AuditEvent]) -> None:
        with self._conn() as c:
            for e in events:
                policy_key = e.policy_ref.key() if e.policy_ref else None
                outcome = e.outcome.value if e.outcome else None
                meta = json.dumps(e.metadata)
                occ = e.occurred_at.isoformat()
                c.execute(
                    "INSERT INTO audit_events (event_type, tenant_id, policy_key, correlation_id, outcome, payload_ref, metadata, occurred_at) VALUES (?,?,?,?,?,?,?,?)",
                    (e.event_type.value, e.tenant_id, policy_key, e.correlation_id, outcome, e.payload_ref, meta, occ),
                )

    # ArtifactStore
    def put(self, key: str, data: bytes) -> str:
        safe = _safe_key(key)
        path = self._artifact_root / safe
        path.write_bytes(data)
        return safe

    def get(self, key: str) -> bytes | None:
        path = self._artifact_root / key
        if not path.exists():
            return None
        return path.read_bytes()

    # AssuranceRunStore
    def create_run(self, tenant_id: TenantId, metadata: dict[str, Any] | None) -> RunId:
        from datetime import datetime, timezone
        rid = new_run_id()
        now = datetime.now(timezone.utc).isoformat()
        summary = json.dumps(metadata or {})
        with self._conn() as c:
            c.execute(
                "INSERT INTO assurance_runs (run_id, tenant_id, status, summary, created_at) VALUES (?,?,?,?,?)",
                (rid, tenant_id, "running", summary, now),
            )
        return rid

    def update_run(
        self,
        run_id: RunId,
        status: str,
        summary: dict[str, Any] | None = None,
    ) -> None:
        if summary is not None:
            with self._conn() as c:
                c.execute(
                    "UPDATE assurance_runs SET status=?, summary=? WHERE run_id=?",
                    (status, json.dumps(summary), run_id),
                )
        else:
            with self._conn() as c:
                c.execute("UPDATE assurance_runs SET status=? WHERE run_id=?", (status, run_id))

    def get_run(self, run_id: RunId) -> AssuranceRunRecord | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT run_id, tenant_id, status, summary, created_at FROM assurance_runs WHERE run_id=?",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        from datetime import datetime
        return AssuranceRunRecord(
            run_id=row[0],
            tenant_id=row[1],
            status=row[2],
            summary=json.loads(row[3]),
            created_at=datetime.fromisoformat(row[4]),
        )
