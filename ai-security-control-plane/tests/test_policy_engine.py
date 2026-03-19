"""Policy engine stub and trust-registry gate tests."""

import tempfile
from pathlib import Path

import pytest

from ascp.core.types import PolicyEvaluationContext
from ascp.policy.engine import AllowAllPolicyEngine, TrustRegistryPolicyEngine
from ascp.storage.sqlite_fs import SqliteFsBackend


def test_allow_all_engine():
    engine = AllowAllPolicyEngine()
    ctx = PolicyEvaluationContext(model_id="any", tenant_id="default")
    decision = engine.evaluate(ctx)
    assert decision.outcome.value == "allow"


def test_trust_registry_blocks_unknown_model():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        art = Path(tmp) / "art"
        backend = SqliteFsBackend(
            database_url=f"sqlite:///{db}",
            artifact_root=str(art),
        )
        backend.register_model("default", "gpt-4")
        engine = TrustRegistryPolicyEngine(backend, require_registration=True)

    ctx_allowed = PolicyEvaluationContext(tenant_id="default", model_id="gpt-4")
    assert engine.evaluate(ctx_allowed).outcome.value == "allow"

    ctx_blocked = PolicyEvaluationContext(tenant_id="default", model_id="gpt-5")
    decision = engine.evaluate(ctx_blocked)
    assert decision.outcome.value == "block"
    assert "TRUST_MODEL_NOT_ALLOWED" in decision.reason_codes
    assert len(decision.violations) == 1
    assert decision.violations[0].code == "TRUST_MODEL_NOT_ALLOWED"


def test_trust_registry_no_model_id_allows():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        backend = SqliteFsBackend(
            database_url=f"sqlite:///{db}",
            artifact_root=str(Path(tmp) / "art"),
        )
        engine = TrustRegistryPolicyEngine(backend, require_registration=True)
    ctx = PolicyEvaluationContext(tenant_id="default", model_id=None)
    assert engine.evaluate(ctx).outcome.value == "allow"


def test_trust_registry_require_registration_false_allows_all():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        backend = SqliteFsBackend(
            database_url=f"sqlite:///{db}",
            artifact_root=str(Path(tmp) / "art"),
        )
        engine = TrustRegistryPolicyEngine(backend, require_registration=False)
    ctx = PolicyEvaluationContext(tenant_id="default", model_id="unknown-model")
    assert engine.evaluate(ctx).outcome.value == "allow"
