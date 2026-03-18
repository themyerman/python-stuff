"""Roundtrip tests for SqliteFsBackend."""

from __future__ import annotations

import sqlite3

import pytest

from ascp.core.types import AuditEvent, AuditEventType, PolicyRef, new_run_id
from ascp.storage import AssuranceRunRecord, SqliteFsBackend


@pytest.fixture
def backend(tmp_path):
    db = tmp_path / "test.db"
    art = tmp_path / "artifacts"
    return SqliteFsBackend(f"sqlite:///{db}", artifact_root=art)


def test_policy_roundtrip(backend):
    ref = PolicyRef(tenant_id="t1", policy_id="p1", version="v1")
    doc = {"rules": [{"action": "allow"}], "meta": {"n": 1}}
    assert backend.get_policy_document(ref) is None
    backend.put_policy_document(ref, doc)
    assert backend.get_policy_document(ref) == doc
    backend.put_policy_document(ref, {"updated": True})
    assert backend.get_policy_document(ref) == {"updated": True}

    ref2 = PolicyRef(tenant_id="t1", policy_id="p1", version="v2")
    backend.put_policy_document(ref2, {"v": 2})
    versions = backend.list_policy_versions("t1", "p1")
    assert len(versions) == 2
    assert {v.version for v in versions} == {"v1", "v2"}


def test_trust_roundtrip(backend):
    assert not backend.is_model_allowed("t1", "gpt-4")
    assert backend.list_models("t1") == []
    backend.register_model("t1", "gpt-4", metadata={"vendor": "openai"})
    assert backend.is_model_allowed("t1", "gpt-4")
    assert "gpt-4" in backend.list_models("t1")
    backend.register_model("t1", "claude-3")
    assert set(backend.list_models("t1")) == {"claude-3", "gpt-4"}


def test_audit_roundtrip(backend):
    ev = AuditEvent(
        event_type=AuditEventType.POLICY_EVALUATION,
        tenant_id="t1",
        correlation_id="cid-1",
        payload={"outcome": "ALLOW"},
    )
    backend.append(ev)
    ev2 = AuditEvent(
        event_type=AuditEventType.SYSTEM,
        tenant_id="t1",
        payload={"k": "v"},
    )
    backend.append_batch([ev2])

    db_path = backend._db_path
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT event_json FROM audit_events ORDER BY id"
        ).fetchall()
    assert len(rows) == 2
    r0 = AuditEvent.model_validate_json(rows[0][0])
    assert r0.event_type == AuditEventType.POLICY_EVALUATION
    assert r0.correlation_id == "cid-1"
    r1 = AuditEvent.model_validate_json(rows[1][0])
    assert r1.event_type == AuditEventType.SYSTEM


def test_artifact_roundtrip(backend):
    key = "runs/r1/output.bin"
    data = b"\x00hello\xff"
    assert backend.get_bytes(key) is None
    assert backend.put_bytes(key, data) == key
    assert backend.get_bytes(key) == data


def test_assurance_run_roundtrip(backend):
    rid = new_run_id()
    rec = AssuranceRunRecord(
        run_id=rid,
        tenant_id="t1",
        workspace_id="ws1",
        status="created",
        metadata={"suite": "jailbreak"},
    )
    assert backend.get_run(rid) is None
    backend.create_run(rec)
    got = backend.get_run(rid)
    assert got is not None
    assert got.run_id == rid
    assert got.status == "created"
    assert got.metadata == {"suite": "jailbreak"}

    backend.update_run(rid, status="completed", metadata={"score": 0.9})
    got2 = backend.get_run(rid)
    assert got2.status == "completed"
    assert got2.metadata == {"suite": "jailbreak", "score": 0.9}


def test_assurance_list_runs_order(backend):
    t = "t1"
    for i in range(3):
        rid = new_run_id()
        backend.create_run(
            AssuranceRunRecord(
                run_id=rid,
                tenant_id=t,
                status="created",
                metadata={"i": i},
            )
        )
    listed = backend.list_runs(t, limit=10)
    assert len(listed) == 3
    assert {r.metadata.get("i") for r in listed} == {0, 1, 2}
