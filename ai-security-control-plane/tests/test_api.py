"""Operator API (requires fastapi)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from starlette.testclient import TestClient

from ascp.api.app import create_app
from ascp.config import Settings


@pytest.fixture
def client(tmp_path):
    db = tmp_path / "api.db"
    art = tmp_path / "art"
    settings = Settings(
        database_url=f"sqlite:///{db}",
        artifact_root=str(art),
    )
    app = create_app(settings)
    with TestClient(app) as tc:
        yield tc


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_evaluate_flow(client):
    tid = "tenant-a"
    client.put(
        f"/v1/tenants/{tid}/policies/default/versions/v1",
        json={
            "schema_version": "1",
            "tools": {
                "mode": "allowlist",
                "allowed": ["search"],
                "deny": [],
                "on_violation": "block",
            },
        },
    )
    client.post(
        f"/v1/tenants/{tid}/models",
        json={"model_id": "gpt-4"},
    )

    ok = client.post(
        f"/v1/tenants/{tid}/evaluate",
        json={
            "policy_id": "default",
            "policy_version": "v1",
            "model_id": "gpt-4",
            "tools_invoked": ["search"],
            "audit": False,
        },
    )
    assert ok.status_code == 200
    assert ok.json()["outcome"] == "ALLOW"

    bad = client.post(
        f"/v1/tenants/{tid}/evaluate",
        json={
            "policy_id": "default",
            "policy_version": "v1",
            "model_id": "gpt-4",
            "tools_invoked": ["bash"],
            "audit": False,
        },
    )
    assert bad.json()["outcome"] == "BLOCK"

    unreg = client.post(
        f"/v1/tenants/{tid}/evaluate",
        json={
            "policy_id": "default",
            "policy_version": "v1",
            "model_id": "unknown",
            "tools_invoked": [],
            "audit": False,
        },
    )
    assert unreg.json()["outcome"] == "BLOCK"
