"""Reference backend: SQLite for metadata + local filesystem for artifact blobs."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from ascp.core.types import AuditEvent, PolicyRef, RunId, TenantId
from ascp.storage.ports import AssuranceRunRecord


def _sqlite_path_from_url(database_url: str) -> Path:
    """Extract filesystem path from sqlite URL (sqlite:///path or sqlite:////absolute)."""
    if database_url.startswith("sqlite:////"):
        return Path(database_url.replace("sqlite:////", "/"))
    if database_url.startswith("sqlite:///"):
        return Path(database_url.replace("sqlite:///", ""))
    if database_url.startswith("sqlite://"):
        return Path(database_url[9:])
    return Path(database_url)


def _safe_artifact_key(key: str) -> str:
    if not key or ".." in key or key.startswith("/"):
        raise ValueError("invalid artifact key")
    if not re.match(r"^[a-zA-Z0-9._/-]+$", key):
        raise ValueError("artifact key must be alphanumeric path segments")
    return key


class SqliteFsBackend:
    """
    Implements PolicyRepository, TrustRegistry, AuditSink, ArtifactStore, AssuranceRunStore.

    - SQLite tables: policies, trust_registry, audit_events, assurance_runs
    - Artifacts stored under ``artifact_root`` as files keyed by relative path.
    """

    def __init__(self, database_url: str, artifact_root: str | Path) -> None:
        self._db_path = _sqlite_path_from_url(database_url)
        self._artifact_root = Path(artifact_root)
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS policies (
                    tenant_id TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    document_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, policy_id, version)
                );
                CREATE TABLE IF NOT EXISTS trust_registry (
                    tenant_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, model_id)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS assurance_runs (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    workspace_id TEXT,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_occurred ON audit_events(occurred_at);
                """
            )

    # --- PolicyRepository ---
    def get_policy_document(self, ref: PolicyRef) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT document_json FROM policies
                WHERE tenant_id = ? AND policy_id = ? AND version = ?
                """,
                (ref.tenant_id, ref.policy_id, ref.version),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["document_json"])

    def put_policy_document(self, ref: PolicyRef, document: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat()
        payload = json.dumps(document, default=str)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO policies (tenant_id, policy_id, version, document_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, policy_id, version) DO UPDATE SET
                    document_json = excluded.document_json
                """,
                (ref.tenant_id, ref.policy_id, ref.version, payload, now),
            )

    def list_policy_versions(self, tenant_id: TenantId, policy_id: str) -> list[PolicyRef]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT version FROM policies
                WHERE tenant_id = ? AND policy_id = ?
                ORDER BY created_at ASC
                """,
                (tenant_id, policy_id),
            ).fetchall()
        return [
            PolicyRef(tenant_id=tenant_id, policy_id=policy_id, version=r["version"])
            for r in rows
        ]

    # --- TrustRegistry ---
    def register_model(
        self,
        tenant_id: TenantId,
        model_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        meta = metadata or {}
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trust_registry (tenant_id, model_id, metadata_json, registered_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tenant_id, model_id) DO UPDATE SET
                    metadata_json = excluded.metadata_json,
                    registered_at = excluded.registered_at
                """,
                (tenant_id, model_id, json.dumps(meta, default=str), now),
            )

    def is_model_allowed(self, tenant_id: TenantId, model_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM trust_registry WHERE tenant_id = ? AND model_id = ?",
                (tenant_id, model_id),
            ).fetchone()
        return row is not None

    def list_models(self, tenant_id: TenantId) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT model_id FROM trust_registry WHERE tenant_id = ? ORDER BY model_id",
                (tenant_id,),
            ).fetchall()
        return [r["model_id"] for r in rows]

    # --- AuditSink ---
    def append(self, event: AuditEvent) -> None:
        self.append_batch([event])

    def append_batch(self, events: list[AuditEvent]) -> None:
        if not events:
            return
        rows = [
            (
                e.model_dump_json(),
                e.occurred_at.isoformat() if e.occurred_at.tzinfo else e.occurred_at.replace(tzinfo=UTC).isoformat(),
            )
            for e in events
        ]
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO audit_events (event_json, occurred_at) VALUES (?, ?)",
                rows,
            )

    # --- ArtifactStore ---
    def put_bytes(self, key: str, data: bytes) -> str:
        sk = _safe_artifact_key(key)
        path = self._artifact_root / sk
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return sk

    def get_bytes(self, key: str) -> bytes | None:
        sk = _safe_artifact_key(key)
        path = self._artifact_root / sk
        if not path.is_file():
            return None
        return path.read_bytes()

    # --- AssuranceRunStore ---
    def create_run(self, record: AssuranceRunRecord) -> RunId:
        now = datetime.now(UTC).isoformat()
        meta = json.dumps(record.metadata, default=str)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assurance_runs
                (run_id, tenant_id, workspace_id, status, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_id,
                    record.tenant_id,
                    record.workspace_id,
                    record.status,
                    meta,
                    now,
                    now,
                ),
            )
        return record.run_id

    def update_run(
        self,
        run_id: RunId,
        *,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT metadata_json, status FROM assurance_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown run_id: {run_id}")
            current_meta = json.loads(row["metadata_json"])
            if metadata:
                current_meta = {**current_meta, **metadata}
            new_status = status if status is not None else row["status"]
            conn.execute(
                """
                UPDATE assurance_runs
                SET status = ?, metadata_json = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (new_status, json.dumps(current_meta, default=str), now, run_id),
            )

    def get_run(self, run_id: RunId) -> AssuranceRunRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM assurance_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return AssuranceRunRecord(
            run_id=row["run_id"],
            tenant_id=row["tenant_id"],
            workspace_id=row["workspace_id"],
            status=row["status"],
            metadata=json.loads(row["metadata_json"]),
        )
