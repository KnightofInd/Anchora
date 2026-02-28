"""
Policy Engine Interface
-----------------------
All policy/compliance enforcement in Anchora MUST go through this interface.

NEVER call compliance logic directly in routes or workflow handlers.
This design allows drop-in OPA replacement later by swapping the evaluator
implementation without touching any business logic.

Migration path to OPA:
    evaluator.py → makes HTTP call to OPA instead of local evaluation.
"""

from abc import ABC, abstractmethod
from typing import Any


class PolicyEngineInterface(ABC):
    """
    Abstract contract for policy evaluation.
    All evaluators (local or OPA) must satisfy this interface.
    """

    @abstractmethod
    async def evaluate(self, payload: dict[str, Any]) -> "PolicyResult":
        """
        Evaluate a payload against all applicable policies.

        Args:
            payload: Contains entity_type, entity_id, action, context, user_role, risk_score, etc.

        Returns:
            PolicyResult with allowed flag, matched policies, and violations.
        """
        raise NotImplementedError


class PolicyResult:
    """Immutable result returned by the policy engine."""

    def __init__(
        self,
        allowed: bool,
        matched_policies: list[str],
        violations: list[str],
        requires_escalation: bool = False,
        notes: str = "",
    ):
        self.allowed = allowed
        self.matched_policies = matched_policies
        self.violations = violations
        self.requires_escalation = requires_escalation
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "matched_policies": self.matched_policies,
            "violations": self.violations,
            "requires_escalation": self.requires_escalation,
            "notes": self.notes,
        }
