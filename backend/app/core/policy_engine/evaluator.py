"""
Policy Engine Evaluator
-----------------------
Local Python implementation of the PolicyEngineInterface.
Evaluates decision payloads against JSON-defined rules loaded from the DB.

OPA Migration: Replace this file's evaluate() with an HTTP call to OPA.
Business logic in modules remains untouched.
"""

import json
import operator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.policy_engine.interface import PolicyEngineInterface, PolicyResult


OPERATORS = {
    ">":  operator.gt,
    ">=": operator.ge,
    "<":  operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


class LocalPolicyEvaluator(PolicyEngineInterface):
    """
    Evaluates JSON logic rules stored in the policies table.

    Rule definition format (stored in policies.rule_definition as JSON):
    {
        "condition": "risk_score > 7",
        "action": "require_senior_approval",
        "severity": "high"
    }
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, payload: dict[str, Any]) -> PolicyResult:
        from app.models.policy import Policy  # avoid circular import

        result = await self.db.execute(select(Policy).where(Policy.is_active == True))
        policies = result.scalars().all()

        matched:    list[str] = []
        violations: list[str] = []
        requires_escalation = False

        for policy in policies:
            rule: dict = policy.rule_definition
            if not rule:
                continue

            condition = rule.get("condition", "")
            action    = rule.get("action", "")

            if self._evaluate_condition(condition, payload):
                matched.append(policy.name)

                if action == "require_senior_approval":
                    requires_escalation = True

                if action == "block":
                    violations.append(
                        f"Policy '{policy.name}' blocks this action: {condition}"
                    )

        allowed = len(violations) == 0
        return PolicyResult(
            allowed=allowed,
            matched_policies=matched,
            violations=violations,
            requires_escalation=requires_escalation,
        )

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _evaluate_condition(self, condition: str, payload: dict) -> bool:
        """
        Parses simple 'field OP value' conditions.
        Example: "risk_score > 7"
        """
        try:
            for op_str, op_fn in OPERATORS.items():
                if op_str in condition:
                    left_key, right_val = condition.split(op_str, 1)
                    left_key  = left_key.strip()
                    right_val = right_val.strip()

                    left = payload.get(left_key)
                    if left is None:
                        return False

                    # Try numeric comparison first
                    try:
                        return op_fn(float(left), float(right_val))
                    except ValueError:
                        return op_fn(str(left), str(right_val))
            return False
        except Exception:
            return False
