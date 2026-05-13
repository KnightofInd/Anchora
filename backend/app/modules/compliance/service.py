from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.compliance import ComplianceCheck, ComplianceStatus
from app.models.decision import Decision
from app.models.policy import Policy
from app.core.policy_engine.evaluator import LocalPolicyEvaluator
from app.core.audit_engine.logger import audit
from app.schemas.compliance_schema import ComplianceCheckRead, ComplianceReportRead
from fastapi import HTTPException, status


class ComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.policy_engine = LocalPolicyEvaluator(db)

    async def run_checks(self, decision: Decision, user_id: str) -> list[ComplianceCheck]:
        """
        Run all active policies against a decision.
        Creates ComplianceCheck records for every policy.
        Called automatically during decision creation.
        """
        policies_result = await self.db.execute(
            select(Policy).where(Policy.is_active == True)
        )
        policies = policies_result.scalars().all()

        checks = []
        for policy in policies:
            result = await self.policy_engine.evaluate({
                "entity_type": "decision",
                "action": "compliance_check",
                "risk_score": decision.risk_score or 0,
                "policy_name": policy.name,
            })

            check = ComplianceCheck(
                decision_id=decision.id,
                policy_id=policy.id,
                status=ComplianceStatus.PASS if result.allowed else ComplianceStatus.FAIL,
                violations=result.violations,
                risk_notes={"requires_escalation": result.requires_escalation, "notes": result.notes},
            )
            self.db.add(check)
            checks.append(check)

        await self.db.flush()

        await audit.log(
            self.db,
            entity_type="decision",
            entity_id=decision.id,
            action="compliance_checked",
            performed_by=user_id,
            metadata={"policies_evaluated": len(policies)},
        )

        return checks

    async def get_report(self, decision_id: str) -> ComplianceReportRead:
        result = await self.db.execute(
            select(ComplianceCheck)
            .where(ComplianceCheck.decision_id == decision_id)
        )
        checks = result.scalars().all()

        overall = "pass" if all(c.status == ComplianceStatus.PASS for c in checks) else "fail"

        return ComplianceReportRead(
            decision_id=decision_id,
            checks=[ComplianceCheckRead.model_validate(c) for c in checks],
            overall_status=overall,
        )
