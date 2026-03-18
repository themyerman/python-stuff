"""Evaluate stored policy documents (tool allowlists, denylists)."""

from __future__ import annotations

from typing import Any

from ascp.core.types import (
    Decision,
    DecisionOutcome,
    PolicyEvaluationContext,
    PolicyRef,
    Violation,
    new_correlation_id,
)
from ascp.policy.document import PolicyDocumentV1
from ascp.storage.ports import PolicyRepository


def _tools_from_context(extra: dict[str, Any]) -> list[str]:
    raw = extra.get("tools_invoked") or extra.get("tools")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, (list, tuple)):
        return [str(t).strip() for t in raw if str(t).strip()]
    return []


class DocumentPolicyEngine:
    """
    Loads ``PolicyDocumentV1`` from ``PolicyRepository`` for a fixed ``PolicyRef``.
    Enforces ``tools`` rules against ``ctx.extra["tools_invoked"]`` (or ``tools``).
    Denied tools always block. Allowlist violations use ``tools.on_violation``.
    """

    def __init__(self, repo: PolicyRepository, *, policy_ref: PolicyRef) -> None:
        self._repo = repo
        self._ref = policy_ref

    def evaluate(self, ctx: PolicyEvaluationContext) -> Decision:
        cid = ctx.correlation_id or new_correlation_id()
        ref = self._ref

        doc_raw = self._repo.get_policy_document(ref)
        if doc_raw is None:
            return Decision(
                outcome=DecisionOutcome.BLOCK,
                violations=[
                    Violation(
                        code="POLICY_NOT_FOUND",
                        reason=f"No policy document for {ref.policy_id!r} version {ref.version!r}",
                        details={
                            "tenant_id": ref.tenant_id,
                            "policy_id": ref.policy_id,
                            "version": ref.version,
                        },
                    )
                ],
                correlation_id=cid,
            )

        try:
            policy = PolicyDocumentV1.from_dict(doc_raw)
        except Exception as e:
            return Decision(
                outcome=DecisionOutcome.BLOCK,
                violations=[
                    Violation(
                        code="POLICY_DOCUMENT_INVALID",
                        reason=str(e),
                        details={"policy_id": ref.policy_id, "version": ref.version},
                    )
                ],
                correlation_id=cid,
            )

        tools = _tools_from_context(ctx.extra)
        tp = policy.tools
        deny_set = {t.lower() for t in tp.deny}
        violations: list[Violation] = []

        for t in tools:
            if t.lower() in deny_set:
                violations.append(
                    Violation(
                        code="TOOL_DENIED",
                        reason=f"Tool {t!r} is denied by policy",
                        details={"tool": t, "policy_id": ref.policy_id},
                    )
                )

        allowed_lower = {x.lower() for x in tp.allowed}
        if tp.mode == "allowlist" and tools:
            for t in tools:
                if t.lower() in deny_set:
                    continue
                if t.lower() not in allowed_lower:
                    violations.append(
                        Violation(
                            code="TOOL_NOT_ALLOWLISTED",
                            reason=f"Tool {t!r} is not in the policy allowlist",
                            details={"tool": t, "allowed": tp.allowed},
                        )
                    )

        if not violations:
            return Decision(outcome=DecisionOutcome.ALLOW, violations=[], correlation_id=cid)

        if any(v.code == "TOOL_DENIED" for v in violations):
            return Decision(outcome=DecisionOutcome.BLOCK, violations=violations, correlation_id=cid)

        allow_v = [v for v in violations if v.code == "TOOL_NOT_ALLOWLISTED"]
        if not allow_v:
            return Decision(outcome=DecisionOutcome.ALLOW, violations=[], correlation_id=cid)

        if tp.on_violation == "block":
            return Decision(outcome=DecisionOutcome.BLOCK, violations=allow_v, correlation_id=cid)
        return Decision(outcome=DecisionOutcome.WARN, violations=allow_v, correlation_id=cid)
