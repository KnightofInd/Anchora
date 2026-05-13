"""
Decision Service
----------------
Core brain of Anchora. Decision creation flow:

1. Chunk-first hybrid retrieval → aggregate relevant documents
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

from app.models.decision import Decision, DecisionReference, DecisionMeetingNote
from app.schemas.decision import DecisionCreate, DecisionMeetingNoteCreate, DecisionMeetingNoteUpdate
from app.core.ai_quality import GroundingEvaluator
from app.core.audit_engine.logger import audit
from app.core.policy_engine.evaluator import LocalPolicyEvaluator
from app.services.ai_service import AIService
from app.models.document import Document
from app.modules.knowledge.service import KnowledgeService
from app.config.settings import settings

logger = logging.getLogger(__name__)


class DecisionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai = AIService()
        self.policy_engine = LocalPolicyEvaluator(db)
        self.knowledge = KnowledgeService(db)

    async def create(
        self,
        payload: DecisionCreate,
        user_id: str,
        user_role: str = "analyst",
    ) -> Decision:
        # ── Step 1: Retrieve relevant documents via chunk-first hybrid search ─
        relevant_docs: list[Document] = []
        retrieval_mode = "semantic_hybrid_chunks"
        try:
            relevant_docs, retrieval_mode = await self.knowledge.retrieve_documents(
                payload.context,
                limit=5,
            )
        except Exception as exc:
            logger.warning("Chunk retrieval failed, falling back to recent docs: %s", exc)

        # Fallback: most recent 3 docs if semantic search found nothing
        if not relevant_docs:
            retrieval_mode = "fallback_recent"
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

        if ai_result.get("ai_unavailable"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Decision generation unavailable: AI provider call failed.",
                    "provider": "gemini",
                    "reason": ai_result.get("ai_error") or "unknown",
                    "attempted_models": ai_result.get("attempted_models") or [],
                    "attempted_model": ai_result.get("model_used"),
                },
            )

        used_model_name = ai_result.get("model_used") or settings.GEMINI_MODEL

        # ── Step 2b: Grounding quality gate ──────────────────────────────────
        ai_citations = ai_result.get("citations", [])
        grounding = GroundingEvaluator.evaluate(
            reasoning_summary=ai_result.get("reasoning_summary", ""),
            context=payload.context,
            retrieved_docs=doc_summaries,
            citations=ai_citations if isinstance(ai_citations, list) else [],
            min_score=settings.AI_GROUNDING_MIN_SCORE,
            require_at_least_one_citation=settings.AI_GROUNDING_REQUIRE_CITATION,
        )
        if settings.AI_GROUNDING_GATE_ENABLED and not grounding.passed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Decision blocked by grounding quality gate.",
                    "grounding": {
                        "score": grounding.score,
                        "citation_coverage": grounding.citation_coverage,
                        "lexical_overlap": grounding.lexical_overlap,
                        "detail": grounding.detail,
                    },
                },
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
            context=payload.context,
            reasoning_summary=ai_result["reasoning_summary"],
            confidence_score=ai_result["confidence_score"],
            risk_score=ai_result["risk_score"],
            assumptions=ai_result["assumptions"],
            ai_model_name=used_model_name,
            ai_model_version=settings.GEMINI_MODEL_VERSION,
            ai_prompt_version=settings.PROMPT_VERSION,
            # Policy version pinning: freeze the evaluated policy snapshot so future
            # policy edits cannot retroactively change this decision's compliance record.
            policy_snapshot=policy_result.to_dict(),
            quality_snapshot={
                "grounding": {
                    "score": grounding.score,
                    "citation_coverage": grounding.citation_coverage,
                    "lexical_overlap": grounding.lexical_overlap,
                    "passed": grounding.passed,
                    "detail": grounding.detail,
                    "citations": ai_citations if isinstance(ai_citations, list) else [],
                },
                "retrieval": {
                    "mode": retrieval_mode,
                    "document_count": len(relevant_docs),
                    "document_titles": [d.title for d in relevant_docs],
                },
                "model": {
                    "name": used_model_name,
                    "version": settings.GEMINI_MODEL_VERSION,
                    "prompt_version": settings.PROMPT_VERSION,
                    "attempted_models": ai_result.get("attempted_models") or [],
                },
            },
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
                "grounding_score": grounding.score,
                "grounding_passed": grounding.passed,
                "grounding_detail": grounding.detail,
                "grounding_citations": ai_citations if isinstance(ai_citations, list) else [],
                "retrieval_mode": retrieval_mode,
                "prompt_version": settings.PROMPT_VERSION,
                "model_version": settings.GEMINI_MODEL_VERSION,
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
            .options(selectinload(Decision.references), selectinload(Decision.meeting_notes))
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

    async def list_paged(
        self,
        *,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        status_filter: str | None = None,
    ) -> list[Decision]:
        sort_columns = {
            "created_at": Decision.created_at,
            "title": Decision.title,
            "risk_score": Decision.risk_score,
            "confidence_score": Decision.confidence_score,
            "status": Decision.status,
        }
        column = sort_columns.get(sort_by, Decision.created_at)
        order_expr = column.asc() if sort_order == "asc" else column.desc()

        query = select(Decision).options(selectinload(Decision.references))
        if status_filter:
            query = query.where(Decision.status == status_filter)

        result = await self.db.execute(
            query
            .order_by(order_expr)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_meeting_notes(self, decision_id: str) -> list[DecisionMeetingNote]:
        await self.get_by_id(decision_id)
        result = await self.db.execute(
            select(DecisionMeetingNote)
            .where(DecisionMeetingNote.decision_id == decision_id)
            .order_by(DecisionMeetingNote.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_meeting_note(
        self,
        decision_id: str,
        payload: DecisionMeetingNoteCreate,
        user_id: str,
    ) -> DecisionMeetingNote:
        await self.get_by_id(decision_id)
        action_items = [item.strip() for item in payload.action_items if item and item.strip()]
        note = DecisionMeetingNote(
            decision_id=decision_id,
            meeting_title=payload.meeting_title,
            transcript_text=payload.transcript_text,
            execution_guidance=payload.execution_guidance,
            action_items=action_items,
            created_by=user_id,
        )
        self.db.add(note)
        await self.db.flush()

        await audit.log(
            self.db,
            entity_type="decision",
            entity_id=decision_id,
            action="meeting_note_added",
            performed_by=user_id,
            metadata={
                "meeting_note_id": str(note.id),
                "has_guidance": bool(payload.execution_guidance and payload.execution_guidance.strip()),
                "action_items_count": len(action_items),
            },
        )
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def update_meeting_note(
        self,
        decision_id: str,
        note_id: str,
        payload: DecisionMeetingNoteUpdate,
        user_id: str,
    ) -> DecisionMeetingNote:
        await self.get_by_id(decision_id)
        result = await self.db.execute(
            select(DecisionMeetingNote)
            .where(
                DecisionMeetingNote.id == note_id,
                DecisionMeetingNote.decision_id == decision_id,
            )
        )
        note = result.scalar_one_or_none()
        if note is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting note not found.")

        update_data = payload.model_dump(exclude_unset=True)
        if "action_items" in update_data and update_data["action_items"] is not None:
            update_data["action_items"] = [
                item.strip()
                for item in update_data["action_items"]
                if isinstance(item, str) and item.strip()
            ]

        for field, value in update_data.items():
            setattr(note, field, value)

        await self.db.flush()
        await audit.log(
            self.db,
            entity_type="decision",
            entity_id=decision_id,
            action="meeting_note_updated",
            performed_by=user_id,
            metadata={
                "meeting_note_id": str(note.id),
                "updated_fields": sorted(update_data.keys()),
            },
        )
        await self.db.commit()
        await self.db.refresh(note)
        return note
