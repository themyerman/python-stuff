"""Policy document schema and DocumentPolicyEngine."""

from __future__ import annotations

import pytest

from ascp.core.types import DecisionOutcome, PolicyEvaluationContext, PolicyRef
from ascp.policy import DocumentPolicyEngine, PolicyDocumentV1, ToolsPolicy, policy_document_from_yaml
from ascp.storage import SqliteFsBackend


@pytest.fixture
def backend(tmp_path):
    return SqliteFsBackend(
        f"sqlite:///{tmp_path / 'd.db'}",
        artifact_root=tmp_path / "a",
    )


def test_policy_document_from_yaml():
    doc = policy_document_from_yaml(
        """
schema_version: "1"
description: test
tools:
  mode: allowlist
  allowed: [read_file, search]
  deny: [bash]
  on_violation: warn
"""
    )
    assert doc.schema_version == "1"
    assert doc.tools.mode == "allowlist"
    assert doc.tools.allowed == ["read_file", "search"]
    assert doc.tools.deny == ["bash"]
    assert doc.tools.on_violation == "warn"


def test_document_engine_allowlist_block(backend):
    ref = PolicyRef(tenant_id="t1", policy_id="p1", version="v1")
    backend.put_policy_document(
        ref,
        PolicyDocumentV1(
            tools=ToolsPolicy(
                mode="allowlist",
                allowed=["read_file"],
                on_violation="block",
            )
        ).to_dict(),
    )

    eng = DocumentPolicyEngine(backend, policy_ref=ref)
    ok = eng.evaluate(
        PolicyEvaluationContext(
            tenant_id="t1",
            extra={"tools_invoked": ["read_file"]},
        )
    )
    assert ok.outcome == DecisionOutcome.ALLOW

    bad = eng.evaluate(
        PolicyEvaluationContext(
            tenant_id="t1",
            extra={"tools_invoked": ["bash"]},
        )
    )
    assert bad.outcome == DecisionOutcome.BLOCK
    assert bad.violations[0].code == "TOOL_NOT_ALLOWLISTED"


def test_document_engine_deny_wins(backend):
    ref = PolicyRef(tenant_id="t1", policy_id="p1", version="v1")
    backend.put_policy_document(
        ref,
        PolicyDocumentV1(
            tools=ToolsPolicy(
                mode="open",
                allowed=[],
                deny=["exec"],
            )
        ).to_dict(),
    )
    eng = DocumentPolicyEngine(backend, policy_ref=ref)
    d = eng.evaluate(
        PolicyEvaluationContext(tenant_id="t1", extra={"tools_invoked": ["exec"]})
    )
    assert d.outcome == DecisionOutcome.BLOCK
    assert d.violations[0].code == "TOOL_DENIED"


def test_document_engine_warn_on_allowlist(backend):
    ref = PolicyRef(tenant_id="t1", policy_id="p1", version="v1")
    backend.put_policy_document(
        ref,
        PolicyDocumentV1(
            tools=ToolsPolicy(
                mode="allowlist",
                allowed=["a"],
                on_violation="warn",
            )
        ).to_dict(),
    )
    eng = DocumentPolicyEngine(backend, policy_ref=ref)
    d = eng.evaluate(
        PolicyEvaluationContext(tenant_id="t1", extra={"tools_invoked": ["b"]})
    )
    assert d.outcome == DecisionOutcome.WARN


def test_policy_not_found(backend):
    ref = PolicyRef(tenant_id="t1", policy_id="missing", version="v1")
    eng = DocumentPolicyEngine(backend, policy_ref=ref)
    d = eng.evaluate(PolicyEvaluationContext(tenant_id="t1"))
    assert d.outcome == DecisionOutcome.BLOCK
    assert d.violations[0].code == "POLICY_NOT_FOUND"


def test_chained_trust_then_tools(backend):
    from ascp.policy import ChainedPolicyEngine, TrustRegistryPolicyEngine

    ref = PolicyRef(tenant_id="t1", policy_id="p1", version="v1")
    backend.register_model("t1", "gpt-4")
    backend.put_policy_document(
        ref,
        PolicyDocumentV1(
            tools=ToolsPolicy(mode="allowlist", allowed=["search"], on_violation="block")
        ).to_dict(),
    )
    chain = ChainedPolicyEngine(
        TrustRegistryPolicyEngine(backend, require_registration=True),
        DocumentPolicyEngine(backend, policy_ref=ref),
    )
    blocked_model = chain.evaluate(
        PolicyEvaluationContext(
            tenant_id="t1",
            model_id="other",
            extra={"tools_invoked": ["search"]},
        )
    )
    assert blocked_model.outcome == DecisionOutcome.BLOCK
    assert blocked_model.violations[0].code == "TRUST_MODEL_NOT_ALLOWED"

    blocked_tool = chain.evaluate(
        PolicyEvaluationContext(
            tenant_id="t1",
            model_id="gpt-4",
            extra={"tools_invoked": ["rm"]},
        )
    )
    assert blocked_tool.outcome == DecisionOutcome.BLOCK
    assert blocked_tool.violations[0].code == "TOOL_NOT_ALLOWLISTED"
