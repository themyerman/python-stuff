"""Policy engine behavior."""

from __future__ import annotations

import pytest

from ascp.core.types import DecisionOutcome, PolicyEvaluationContext
from ascp.policy import AllowAllPolicyEngine, TrustRegistryPolicyEngine
from ascp.storage import SqliteFsBackend


@pytest.fixture
def trust_backend(tmp_path):
    db = tmp_path / "t.db"
    return SqliteFsBackend(f"sqlite:///{db}", artifact_root=tmp_path / "a")


def test_allow_all():
    eng = AllowAllPolicyEngine()
    d = eng.evaluate(
        PolicyEvaluationContext(tenant_id="t1", model_id="anything")
    )
    assert d.outcome == DecisionOutcome.ALLOW
    assert d.violations == []


def test_trust_registry_blocks_unknown_model(trust_backend):
    trust_backend.register_model("t1", "allowed-model")
    eng = TrustRegistryPolicyEngine(trust_backend, require_registration=True)

    ok = eng.evaluate(
        PolicyEvaluationContext(tenant_id="t1", model_id="allowed-model")
    )
    assert ok.outcome == DecisionOutcome.ALLOW

    blocked = eng.evaluate(
        PolicyEvaluationContext(tenant_id="t1", model_id="unknown-model")
    )
    assert blocked.outcome == DecisionOutcome.BLOCK
    assert len(blocked.violations) == 1
    assert blocked.violations[0].code == "TRUST_MODEL_NOT_ALLOWED"
    assert "unknown-model" in blocked.violations[0].reason
