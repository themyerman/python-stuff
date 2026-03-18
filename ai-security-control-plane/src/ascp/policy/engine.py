"""Policy engine protocol and built-in engines."""

from __future__ import annotations

from typing import Protocol

from ascp.core.types import (
    Decision,
    DecisionOutcome,
    PolicyEvaluationContext,
    Violation,
    new_correlation_id,
)
from ascp.storage.ports import TrustRegistry


class PolicyEngine(Protocol):
    def evaluate(self, ctx: PolicyEvaluationContext) -> Decision: ...


class AllowAllPolicyEngine:
    """Always returns ALLOW."""

    def evaluate(self, ctx: PolicyEvaluationContext) -> Decision:
        cid = ctx.correlation_id or new_correlation_id()
        return Decision(outcome=DecisionOutcome.ALLOW, violations=[], correlation_id=cid)


class TrustRegistryPolicyEngine:
    """
    When ``require_registration`` is True: if ``model_id`` is set and the model is not
    in the tenant registry, returns BLOCK with ``TRUST_MODEL_NOT_ALLOWED``.

    When ``require_registration`` is False, always ALLOW (registry not enforced).
    """

    def __init__(self, trust: TrustRegistry, *, require_registration: bool = True) -> None:
        self._trust = trust
        self._require_registration = require_registration

    def evaluate(self, ctx: PolicyEvaluationContext) -> Decision:
        cid = ctx.correlation_id or new_correlation_id()
        if not self._require_registration:
            return Decision(outcome=DecisionOutcome.ALLOW, violations=[], correlation_id=cid)

        mid = (ctx.model_id or "").strip()
        if not mid:
            return Decision(outcome=DecisionOutcome.ALLOW, violations=[], correlation_id=cid)

        if not self._trust.is_model_allowed(ctx.tenant_id, mid):
            return Decision(
                outcome=DecisionOutcome.BLOCK,
                violations=[
                    Violation(
                        code="TRUST_MODEL_NOT_ALLOWED",
                        reason=f"Model {mid!r} is not registered for tenant {ctx.tenant_id!r}",
                        details={"model_id": mid, "tenant_id": ctx.tenant_id},
                    )
                ],
                correlation_id=cid,
            )
        return Decision(outcome=DecisionOutcome.ALLOW, violations=[], correlation_id=cid)


class ChainedPolicyEngine:
    """
    Runs multiple engines in order. First **BLOCK** wins; otherwise **WARN** if any
    engine warned; else **ALLOW**. Uses a single correlation id across the chain.
    """

    def __init__(self, *engines: PolicyEngine) -> None:
        if not engines:
            raise ValueError("ChainedPolicyEngine needs at least one engine")
        self._engines = engines

    def evaluate(self, ctx: PolicyEvaluationContext) -> Decision:
        cid = ctx.correlation_id or new_correlation_id()
        ctx = ctx.model_copy(update={"correlation_id": cid})
        merged_violations: list[Violation] = []
        worst: DecisionOutcome = DecisionOutcome.ALLOW

        for eng in self._engines:
            d = eng.evaluate(ctx)
            cid = d.correlation_id or cid
            if d.outcome == DecisionOutcome.BLOCK:
                return Decision(
                    outcome=DecisionOutcome.BLOCK,
                    violations=d.violations,
                    correlation_id=cid,
                )
            if d.outcome == DecisionOutcome.WARN:
                worst = DecisionOutcome.WARN
                merged_violations.extend(d.violations)

        return Decision(outcome=worst, violations=merged_violations, correlation_id=cid)
