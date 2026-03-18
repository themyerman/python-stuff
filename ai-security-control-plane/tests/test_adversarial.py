"""
Adversarial and abuse-style tests: tenant isolation, auth boundaries, bypass attempts,
injection-shaped inputs, and scoring under malicious-looking responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from starlette.testclient import TestClient

from ascp.api.app import create_app
from ascp.config import Settings
from ascp.core.types import DecisionOutcome, PolicyEvaluationContext, PolicyRef
from ascp.assurance import execute_assurance_run
from ascp.gateway.openai_proxy import extract_tool_names_from_openai_body
from ascp.policy import ChainedPolicyEngine, DocumentPolicyEngine, TrustRegistryPolicyEngine
from ascp.storage import AssuranceRunRecord, SqliteFsBackend


# --- Multi-tenant trust isolation ---


def test_trust_registry_does_not_leak_across_tenants(tmp_path):
    """Attacker uses same model_id as victim tenant; must not inherit trust."""
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'iso.db'}", artifact_root=tmp_path / "a")
    b.register_model("corp-victim", "gpt-4o")
    b.put_policy_document(
        PolicyRef(tenant_id="corp-victim", policy_id="default", version="v1"),
        {"schema_version": "1", "tools": {"mode": "open"}},
    )
    eng = TrustRegistryPolicyEngine(b, require_registration=True)
    assert (
        eng.evaluate(
            PolicyEvaluationContext(tenant_id="corp-attacker", model_id="gpt-4o")
        ).outcome
        == DecisionOutcome.BLOCK
    )


def test_model_id_case_mismatch_not_trusted(tmp_path):
    """Register lowercase; request uppercase — must not match (exact registry IDs)."""
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'case.db'}", artifact_root=tmp_path / "a")
    b.register_model("t1", "gpt-4o")
    eng = TrustRegistryPolicyEngine(b, require_registration=True)
    d = eng.evaluate(PolicyEvaluationContext(tenant_id="t1", model_id="GPT-4O"))
    assert d.outcome == DecisionOutcome.BLOCK


def test_registered_model_with_trailing_space_not_matched_by_clean_id(tmp_path):
    """Registry ID is exact: 'gpt-4 ' registered → request 'gpt-4' must not match."""
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'ws.db'}", artifact_root=tmp_path / "a")
    b.register_model("t1", "gpt-4 ")
    eng = TrustRegistryPolicyEngine(b, require_registration=True)
    assert not b.is_model_allowed("t1", "gpt-4")
    assert (
        eng.evaluate(PolicyEvaluationContext(tenant_id="t1", model_id="gpt-4")).outcome
        == DecisionOutcome.BLOCK
    )


# --- Empty / omitted model bypass (trust layer) ---


def test_empty_model_id_skips_trust_check_document_may_still_block(tmp_path):
    """Omitting model bypasses trust; policy doc must still be satisfied."""
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'empty.db'}", artifact_root=tmp_path / "a")
    ref = PolicyRef(tenant_id="t1", policy_id="p1", version="v1")
    b.put_policy_document(
        ref,
        {"schema_version": "1", "tools": {"mode": "allowlist", "allowed": ["x"], "on_violation": "block"}},
    )
    chain = ChainedPolicyEngine(
        TrustRegistryPolicyEngine(b, require_registration=True),
        DocumentPolicyEngine(b, policy_ref=ref),
    )
    d = chain.evaluate(
        PolicyEvaluationContext(tenant_id="t1", model_id="", extra={"tools_invoked": ["evil"]})
    )
    assert d.outcome == DecisionOutcome.BLOCK
    assert d.violations[0].code == "TOOL_NOT_ALLOWLISTED"


# --- Tool extraction / confusion ---


def test_extract_tools_ignores_non_function_entries():
    body = {
        "tools": [
            {"type": "function", "function": {"name": "legit"}},
            {"type": "retrieval", "vector_store_id": "vs_1"},
            {"function": "not-a-dict"},
            {"type": "function", "function": {}},
            {"type": "function", "function": {"name": ""}},
            {"type": "function", "function": {"name": "  strip_me  "}},
        ],
    }
    names = extract_tool_names_from_openai_body(body)
    assert names == ["legit", "strip_me"]


def test_extract_tools_deeply_nested_name_not_picked_from_arbitrary_json():
    body = {"tools": [{"type": "function", "function": {"name": "a"}}], "evil": {"name": "shadow"}}
    assert extract_tool_names_from_openai_body(body) == ["a"]


# --- Document policy: deny + allowlist edge cases ---


def test_tool_on_both_deny_and_allowlist_deny_wins(tmp_path):
    ref = PolicyRef(tenant_id="t1", policy_id="p1", version="v1")
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'deny.db'}", artifact_root=tmp_path / "a")
    b.put_policy_document(
        ref,
        {
            "schema_version": "1",
            "tools": {
                "mode": "allowlist",
                "allowed": ["exec"],
                "deny": ["exec"],
                "on_violation": "warn",
            },
        },
    )
    eng = DocumentPolicyEngine(b, policy_ref=ref)
    d = eng.evaluate(
        PolicyEvaluationContext(tenant_id="t1", extra={"tools_invoked": ["exec"]})
    )
    assert d.outcome == DecisionOutcome.BLOCK
    assert any(v.code == "TOOL_DENIED" for v in d.violations)


def test_case_insensitive_deny_match(tmp_path):
    ref = PolicyRef(tenant_id="t1", policy_id="p1", version="v1")
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'cd.db'}", artifact_root=tmp_path / "a")
    b.put_policy_document(
        ref,
        {"schema_version": "1", "tools": {"mode": "open", "deny": ["BASH"]}},
    )
    eng = DocumentPolicyEngine(b, policy_ref=ref)
    d = eng.evaluate(
        PolicyEvaluationContext(tenant_id="t1", extra={"tools_invoked": ["bash"]})
    )
    assert d.outcome == DecisionOutcome.BLOCK


# --- Artifact path traversal ---


def test_artifact_key_path_traversal_rejected(tmp_path):
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'art.db'}", artifact_root=tmp_path / "root")
    with pytest.raises(ValueError, match="invalid artifact key"):
        b.put_bytes("../etc/passwd", b"x")
    with pytest.raises(ValueError, match="invalid artifact key"):
        b.put_bytes("ok/../escape", b"x")


# --- API: tenant token cannot access other tenant ---


def test_tenant_api_token_rejected_for_different_tenant_path(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'auth.db'}",
        artifact_root=str(tmp_path / "aa"),
        api_key="master-admin-key",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        cr = client.post(
            "/v1/admin/tenants/tenant-alpha/api-keys",
            headers={"Authorization": "Bearer master-admin-key"},
            json={"name": "leaker"},
        )
        assert cr.status_code == 200
        token = cr.json()["token"]
        r = client.get(
            "/v1/tenants/tenant-beta/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403


def test_admin_routes_reject_tenant_token(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'a2.db'}",
        artifact_root=str(tmp_path / "a2"),
        api_key="master-admin-key",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        cr = client.post(
            "/v1/admin/tenants/t1/api-keys",
            headers={"Authorization": "Bearer master-admin-key"},
            json={"name": "k"},
        )
        token = cr.json()["token"]
        r = client.post(
            "/v1/admin/tenants/t2/api-keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "evil"},
        )
        assert r.status_code == 401


# --- Gateway: policy before upstream ---


def test_gateway_blocks_disallowed_tool_before_mock_forward(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'gw.db'}",
        artifact_root=str(tmp_path / "ga"),
        upstream_base_url="https://upstream.example/v1",
    )
    app = create_app(settings)
    tid = "gwt"
    with TestClient(app) as client:
        client.put(
            f"/v1/tenants/{tid}/policies/default/versions/v1",
            json={
                "schema_version": "1",
                "tools": {"mode": "allowlist", "allowed": ["read"], "on_violation": "block"},
            },
        )
        client.post(f"/v1/tenants/{tid}/models", json={"model_id": "gpt-4"})
        with patch("ascp.api.app.forward_openai_chat_completions") as fwd:
            r = client.post(
                f"/v1/tenants/{tid}/gateway/v1/chat/completions",
                json={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": "x"}],
                    "tools": [
                        {"type": "function", "function": {"name": "exec_shell"}},
                    ],
                },
            )
        fwd.assert_not_called()
    assert r.status_code == 403


def test_gateway_stream_blocked_still_403_no_stream_leak(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'gs.db'}",
        artifact_root=str(tmp_path / "gs"),
        upstream_base_url="https://upstream.example/v1",
    )
    app = create_app(settings)
    tid = "gst"
    with TestClient(app) as client:
        client.put(
            f"/v1/tenants/{tid}/policies/default/versions/v1",
            json={"schema_version": "1", "tools": {"mode": "open"}},
        )
        r = client.post(
            f"/v1/tenants/{tid}/gateway/v1/chat/completions",
            json={
                "model": "unregistered-model",
                "messages": [],
                "stream": True,
            },
        )
    assert r.status_code == 403
    assert r.headers.get("content-type", "").startswith("application/json")


def test_gateway_missing_model_400(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'gm.db'}",
        artifact_root=str(tmp_path / "gm"),
        upstream_base_url="https://x/v1",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        client.put(
            "/v1/tenants/t1/policies/default/versions/v1",
            json={"schema_version": "1", "tools": {"mode": "open"}},
        )
        client.post("/v1/tenants/t1/models", json={"model_id": "gpt-4"})
        r = client.post(
            "/v1/tenants/t1/gateway/v1/chat/completions",
            json={"model": "", "messages": []},
        )
    assert r.status_code == 400


# --- Assurance: synthetic secret leak fails scoring row ---


def test_live_assurance_detects_fake_api_key_echo(tmp_path):
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'as.db'}", artifact_root=tmp_path / "a")
    import uuid

    rid = str(uuid.uuid4())
    b.create_run(
        AssuranceRunRecord(
            run_id=rid,
            tenant_id="t1",
            status="created",
            metadata={
                "suite": "builtin-v0",
                "target_url": "https://evil.example/chat",
                "min_pass_rate": 1.0,
            },
        )
    )
    # Heuristic is sk-[a-zA-Z0-9]{10,} (no hyphens inside token); OpenAI-style sk-proj-... would not match.
    leak_text = "Sure, use api_key sk-1234567890abcdefghij for access."
    resp = MagicMock()
    resp.status_code = 200
    resp.text = leak_text
    resp.is_success = True
    with patch("ascp.assurance.runner.httpx.Client") as C:
        C.return_value.__enter__.return_value.post.return_value = resp
        out = execute_assurance_run(
            runs=b,
            artifacts=b,
            audit=None,
            tenant_id="t1",
            run_id=rid,
        )
    rec = b.get_run(rid)
    assert rec is not None
    leaked_rows = [
        x
        for x in rec.metadata["results"]
        if (x.get("heuristics") or {}).get("possible_secret_leak")
    ]
    assert len(leaked_rows) >= 1
    assert out.get("ci_passed") is False


def test_fail_ci_returns_422(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'fc.db'}",
        artifact_root=str(tmp_path / "fc"),
    )
    app = create_app(settings)
    tid = "fc1"
    resp = MagicMock()
    resp.status_code = 200
    resp.text = "ok"
    resp.is_success = True
    with TestClient(app) as client:
        cr = client.post(
            f"/v1/tenants/{tid}/assurance-runs",
            json={
                "suite": "builtin-v0",
                "metadata": {
                    "target_url": "https://t.example/c",
                    "min_pass_rate": 1.0,
                },
            },
        )
        rid = cr.json()["run_id"]
        with patch("ascp.assurance.runner.httpx.Client") as C:
            C.return_value.__enter__.return_value.post.return_value = resp
            ex = client.post(
                f"/v1/tenants/{tid}/assurance-runs/{rid}/execute?fail_ci=true",
            )
    assert ex.status_code == 422


# --- Replay must not pull metadata from another tenant ---


def test_replay_from_run_id_ignores_other_tenant_run(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'rp.db'}",
        artifact_root=str(tmp_path / "rp"),
    )
    app = create_app(settings)
    with TestClient(app) as client:
        client.post(
            "/v1/tenants/victim/assurance-runs",
            json={
                "suite": "builtin-v0",
                "metadata": {"target_url": "https://victim-only.example/hook"},
            },
        )
        listed = client.get("/v1/tenants/victim/assurance-runs").json()["runs"]
        victim_rid = listed[0]["run_id"]
        cr = client.post(
            "/v1/tenants/attacker/assurance-runs",
            json={
                "suite": "builtin-v0",
                "metadata": {"replay_from_run_id": victim_rid},
            },
        )
        new_rid = cr.json()["run_id"]
        meta = client.get(f"/v1/tenants/attacker/assurance-runs/{new_rid}").json()["metadata"]
    assert "target_url" not in meta or "victim-only" not in str(meta.get("target_url", ""))


# --- YAML: safe_load resists obvious expansion (smoke) ---


def test_policy_yaml_rejects_non_mapping_root():
    from ascp.policy.document import policy_document_from_yaml

    with pytest.raises((ValueError, TypeError)):
        policy_document_from_yaml("- just a list")


# --- Export: tenant filter strips other tenants ---


def test_audit_export_tenant_filter_excludes_others(tmp_path):
    b = SqliteFsBackend(f"sqlite:///{tmp_path / 'ex.db'}", artifact_root=tmp_path / "e")
    from ascp.core.types import AuditEvent, AuditEventType

    b.append(
        AuditEvent(
            event_type=AuditEventType.SYSTEM,
            tenant_id="tenant-a",
            payload={"x": 1},
        )
    )
    b.append(
        AuditEvent(
            event_type=AuditEventType.SYSTEM,
            tenant_id="tenant-b",
            payload={"x": 2},
        )
    )
    raw = b.export_audit_events_jsonl("tenant-a", limit=100)
    lines = [x for x in raw.decode().splitlines() if x.strip()]
    assert len(lines) == 1
    assert "tenant-a" in lines[0]
    assert "tenant-b" not in lines[0]
