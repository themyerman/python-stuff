"""Policy engine port and stub implementations."""

from typing import Protocol

from ascp.core.types import Decision, DecisionOutcome, PolicyEvaluationContext, Violation
from ascp.storage.ports import TrustRegistry


class PolicyEngine(Protocol):
    """Evaluate policy for a request; used by gateway and tests."""

    def evaluate(self, ctx: PolicyEvaluationContext) -> Decision:
        ...


class AllowAllPolicyEngine:
    """Stub: allow every request."""

    def evaluate(self, ctx: PolicyEvaluationContext) -> Decision:
        return Decision(outcome=DecisionOutcome.ALLOW)


class TrustRegistryPolicyEngine:
    """Deny if model_id is set and not in trust registry (when require_registration=True)."""

    def __init__(self, trust: TrustRegistry, require_registration: bool = True):
        self._trust = trust
        self._require_registration = require_registration

    def evaluate(self, ctx: PolicyEvaluationContext) -> Decision:
        if not self._require_registration:
            return Decision(outcome=DecisionOutcome.ALLOW)
        if not ctx.model_id:
            return Decision(outcome=DecisionOutcome.ALLOW)
        if self._trust.is_model_allowed(ctx.tenant_id, ctx.model_id):
            return Decision(outcome=DecisionOutcome.ALLOW)
        return Decision(
            outcome=DecisionOutcome.BLOCK,
            reason_codes=["TRUST_MODEL_NOT_ALLOWED"],
            violations=[
                Violation(
                    code="TRUST_MODEL_NOT_ALLOWED",
                    message=f"Model {ctx.model_id} is not in the trust registry",
                    detail={"model_id": ctx.model_id, "tenant_id": ctx.tenant_id},
                )
            ],
        )
