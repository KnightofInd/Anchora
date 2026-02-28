"""
Decision Service
----------------
Core brain of Anchora. Decision creation flow:

1. Semantic search → retrieve relevant documents (graceful fallback to recent docs)
2. Gemini AI → reasoning_summary, assumptions, confidence_score, risk_score
3. Policy engine pre-check against all active rules
4. Store Decision object + DecisionReferences (full traceability)
5. Audit log (append-only)

NEVER auto-execute a decision.
Decision object is immutable once approved.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.decision import Decision, DecisionReference
from app.schemas.decision import DecisionCreate
from app.core.audit_engine.logger import audit
from app.core.policy_engine.evaluator import LocalPolicyEvaluator
from app.services.ai_service import AIService
from app.services.embedding import EmbeddingService
from app.models.document import Document
from app.config.settings import settings

logger = logging.getLogger(__name__)


class DecisionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai = AIService()
        self.policy_engine = LocalPolicyEvaluator(db)
        self.embedding_svc = EmbeddingService()

    async def create(
        self,
        payload: DecisionCreate,
        user_id: str,
        user_role: str = "analyst",
    ) -> Decision:
        # ── Step 1: Retrieve relevant documents via semantic search ───────────
        relevant_docs: list[Document] = []
        try:
            query_embedding = await self.embedding_svc.generate(payload.context)
            docs_result = await self.db.execute(
                select(Document)
                .where(Document.embedding.is_not(None))
                .order_by(Document.embedding.cosine_distance(query_embedding))
                .limit(5)
            )
            relevant_docs = list(docs_result.scalars().all())
        except Exception as exc:
            logger.warning("Semantic doc retrieval failed, falling back to recent docs: %s", exc)

        # Fallback: most recent 3 docs if semantic search found nothing
        if not relevant_docs:
            fallback = await self.db.execute(
                select(Document).order_by(Document.created_at.desc()).limit(3)
            )
            relevant_docs = list(fallback.scalars().all())

        doc_summaries = [{"id": str(d.id), "title": d.title} for d in relevant_docs]

        # ── Step 2: AI recommendation ─────────────────────────────────────────
        ai_result = await self.ai.generate_decision_recommendation(
            title=payload.title,
            description=payload.description or "",
            context=payload.context,
            document_summaries=doc_summaries,
        )

        # ── Step 3: Policy engine pre-check ───────────────────────────────────
        policy_result = await self.policy_engine.evaluate({
            "entity_type": "decision",
            "action": "create",
            "risk_score": ai_result["risk_score"],
            "confidence_score": ai_result["confidence_score"],
            "user_role": user_role,
        })

        # Hard-block only if policy engine explicitly disallows
        if not policy_result.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Decision blocked by policy engine.",
                    "violations": policy_result.violations,
                },
            )

        # ── Step 4: Persist Decision ───────────────────────────────────────────
        decision = Decision(
            title=payload.title,
            description=payload.description,
            reasoning_summary=ai_result["reasoning_summary"],
            confidence_score=ai_result["confidence_score"],
            risk_score=ai_result["risk_score"],
            assumptions=ai_result["assumptions"],
            ai_model_name=settings.GEMINI_MODEL,
            ai_model_version=settings.GEMINI_MODEL_VERSION,
            ai_prompt_version=settings.PROMPT_VERSION,
            created_by=user_id,
        )
        self.db.add(decision)
        await self.db.flush()

        # ── Step 5: Store DecisionReferences (traceability) ───────────────────
        for doc in relevant_docs:
            ref = DecisionReference(
                decision_id=decision.id,
                document_id=doc.id,
                reference_type="document",
                data_source=doc.source,
            )
            self.db.add(ref)
        await self.db.flush()

        # ── Step 5b: Run compliance checks (non-fatal) ────────────────────────
        try:
            from app.modules.compliance.service import ComplianceService
            await ComplianceService(self.db).run_checks(decision, user_id)
        except Exception as exc:
            logger.warning("Compliance checks failed (non-fatal): %s", exc)

        # ── Step 6: Audit log ─────────────────────────────────────────────────
        await audit.log(
            self.db,
            entity_type="decision",
            entity_id=decision.id,
            action="created",
            performed_by=user_id,
            metadata={
                "risk_score": ai_result["risk_score"],
                "confidence_score": ai_result["confidence_score"],
                "requires_escalation": policy_result.requires_escalation,
                "policy_violations": policy_result.violations,
                "document_ids": [str(d.id) for d in relevant_docs],
            },
        )

        await self.db.commit()

        # Reload with references for the response
        result = await self.db.execute(
            select(Decision)
            .options(selectinload(Decision.references))
            .where(Decision.id == decision.id)
        )
        return result.scalar_one()

    async def update_status(
        self,
        decision_id: str,
        new_status: str,
        user_id: str,
        notes: str | None = None,
    ) -> Decision:
        """
        Transition a decision's status.
        Valid transitions: draft→approved, draft→rejected, approved→executed.
        Immutable once approved (cannot go back to draft).
        """
        decision = await self.get_by_id(decision_id)
        previous_status = decision.status

        ALLOWED_TRANSITIONS: dict[str, set[str]] = {
            "draft":    {"approved", "rejected"},
            "approved": {"executed"},
            "rejected": set(),
            "executed": set(),
        }
        allowed = ALLOWED_TRANSITIONS.get(decision.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot transition from '{decision.status}' to '{new_status}'.",
            )

        decision.status = new_status
        if notes and decision.assumptions is not None:
            decision.assumptions = {**decision.assumptions, "transition_note": notes} \
                if isinstance(decision.assumptions, dict) else decision.assumptions
        await self.db.flush()

        await audit.log(
            self.db,
            entity_type="decision",
            entity_id=decision.id,
            action=f"status_changed_to_{new_status}",
            performed_by=user_id,
            metadata={"previous_status": previous_status, "new_status": new_status, "notes": notes},
        )
        await self.db.commit()
        result = await self.db.execute(
            select(Decision)
            .options(selectinload(Decision.references))
            .where(Decision.id == decision.id)
        )
        return result.scalar_one()

    async def get_by_id(self, decision_id: str) -> Decision:
        result = await self.db.execute(
            select(Decision)
            .options(selectinload(Decision.references))
            .where(Decision.id == decision_id)
        )
        decision = result.scalar_one_or_none()
        if not decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Decision not found.",
            )
        return decision

    async def list_all(self) -> list[Decision]:
        result = await self.db.execute(
            select(Decision)
            .options(selectinload(Decision.references))
            .order_by(Decision.created_at.desc())
        )
        return list(result.scalars().all())
