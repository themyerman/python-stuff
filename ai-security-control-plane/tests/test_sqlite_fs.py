"""Round-trip tests for SqliteFsBackend."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from ascp.core.types import (
    AuditEvent,
    AuditEventType,
    DecisionOutcome,
    PolicyRef,
)
from ascp.storage.sqlite_fs import SqliteFsBackend


@pytest.fixture
def backend():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        art = Path(tmp) / "artifacts"
        yield SqliteFsBackend(
            database_url=f"sqlite:///{db}",
            artifact_root=str(art),
        )


def test_policy_roundtrip(backend):
    ref = PolicyRef(tenant_id="t1", name="default", version="1")
    doc = {"tools": ["search"], "model": "gpt-4"}
    backend.put_policy_document(ref, doc)
    got = backend.get_policy_document(ref)
    assert got == doc
    versions = backend.list_policy_versions("t1")
    assert len(versions) == 1
    assert versions[0].key() == ref.key()


def test_trust_registry(backend):
    backend.register_model("t1", "gpt-4", digest="sha256:abc")
    assert backend.is_model_allowed("t1", "gpt-4") is True
    assert backend.is_model_allowed("t1", "gpt-5") is False
    models = backend.list_models("t1")
    assert models == [("gpt-4", "sha256:abc")]


def test_audit_sink(backend):
    ev = AuditEvent(
        event_type=AuditEventType.POLICY_EVALUATION,
        tenant_id="t1",
        outcome=DecisionOutcome.BLOCK,
        correlation_id="cid-1",
    )
    backend.append(ev)
    backend.append_batch([ev])
    db_path = backend._db_path.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as c:
        n = c.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
    assert n == 2


def test_artifact_store(backend):
    key = backend.put("trace-1", b"binary data")
    assert key
    assert backend.get(key) == b"binary data"
    assert backend.get("nonexistent") is None


def test_assurance_run(backend):
    rid = backend.create_run("t1", {"scenario": "injection"})
    assert rid
    rec = backend.get_run(rid)
    assert rec is not None
    assert rec.tenant_id == "t1"
    assert rec.status == "running"
    assert rec.summary.get("scenario") == "injection"
    backend.update_run(rid, "completed", {"score": 0.9})
    rec2 = backend.get_run(rid)
    assert rec2 is not None
    assert rec2.status == "completed"
    assert rec2.summary.get("score") == 0.9
