"""
AI Service (Gemini)
-------------------
All Gemini API calls go through this service.
Every call stores: model_name, model_version, prompt_version, timestamp,
confidence_score, source_document_ids — for academic reproducibility.
"""

import asyncio
import functools
import json
import logging
from typing import Any

from google import genai  # type: ignore[import]
from google.genai import types  # type: ignore[import]

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Lazy-initialized — deferred until first call so the server can start
# even when GEMINI_API_KEY is not yet configured.
_client: "genai.Client | None" = None


def _get_client() -> "genai.Client":
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Add it to backend/.env to enable AI features."
            )
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


DECISION_PROMPT_TEMPLATE = """
You are Anchora, an enterprise decision intelligence system.

Given the following input, generate a structured decision recommendation.

Decision Title: {title}
Description: {description}
Context: {context}

Relevant Documents:
{documents}

Respond ONLY in the following JSON format:
{{
    "reasoning_summary": "...",
    "assumptions": ["...", "..."],
    "confidence_score": 0.0,
    "risk_score": 0.0,
    "risk_factors": ["...", "..."],
    "citations": [
        {{
            "document_id": "<id from Relevant Documents list>",
            "document_title": "<exact title from Relevant Documents list>",
            "evidence_quote": "<short supporting quote or paraphrase>"
        }}
    ]
}}

Rules:
- confidence_score: float 0.0–1.0
- risk_score: float 0.0–10.0
- Be explicit about assumptions
- Include at least one citation when Relevant Documents are provided
- citation.document_id must match an ID from Relevant Documents
- Do not invent document IDs or titles
"""


class AIService:
    @staticmethod
    def _coerce_float(value: Any, default: float) -> float:
        # Narrow to types accepted by float() for static type checkers.
        if not isinstance(value, (int, float, str, bytes, bytearray)):
            return default
        try:
            return float(value)
        except ValueError:
            return default

    @staticmethod
    def _normalize_confidence(value: Any) -> float:
        confidence = AIService._coerce_float(value, 0.5)
        # Some models may return percentages (e.g. 83) instead of 0.83.
        if confidence > 1.0 and confidence <= 100.0:
            confidence = confidence / 100.0
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _normalize_risk(value: Any) -> float:
        risk = AIService._coerce_float(value, 5.0)
        # Some models may return percentages (e.g. 85) instead of 8.5.
        if risk > 10.0 and risk <= 100.0:
            risk = risk / 10.0
        return max(0.0, min(10.0, risk))

    @staticmethod
    def _is_quota_or_resource_exhausted(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "resource_exhausted" in message
            or "quota exceeded" in message
            or "429" in message
        )

    def _sync_generate_with_fallback(self, prompt: str) -> tuple[str, str, list[str]]:
        candidate_models = ["gemini-2.5-flash", "gemini-1.5-flash"]
        attempted_models: list[str] = []
        last_exception: Exception | None = None

        for model_name in candidate_models:
            attempted_models.append(model_name)
            logger.info("Gemini generate_content attempt model=%s", model_name)
            try:
                response = _get_client().models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                return (response.text or "", model_name, attempted_models)
            except Exception as exc:
                last_exception = exc
                logger.warning("Gemini generate_content failed for model=%s: %s", model_name, exc)
                if not self._is_quota_or_resource_exhausted(exc):
                    break

        assert last_exception is not None
        raise RuntimeError(
            f"Gemini generation failed after attempts={attempted_models}. Last error: {last_exception}"
        )

    async def generate_decision_recommendation(
        self,
        title: str,
        description: str,
        context: str,
        document_summaries: list[dict],
    ) -> dict:
        """
        Calls Gemini to generate a decision recommendation.
        Returns structured dict with reasoning, assumptions, scores.
        Runs in thread pool to avoid blocking the event loop.
        """
        doc_text = "\n".join([f"- [{d['id']}] {d['title']}" for d in document_summaries])

        prompt = DECISION_PROMPT_TEMPLATE.format(
            title=title,
            description=description,
            context=context,
            documents=doc_text or "No documents provided.",
        )

        loop = asyncio.get_event_loop()
        attempted_models: list[str] = []
        used_model: str | None = None
        try:
            raw_text, used_model, attempted_models = await loop.run_in_executor(
                None,
                functools.partial(self._sync_generate_with_fallback, prompt),
            )
        except Exception as exc:
            logger.warning("Gemini generate_content failed, using fallback: %s", exc)
            return {
                "reasoning_summary": "AI service unavailable — manual review required.",
                "assumptions": [],
                "confidence_score": 0.5,
                "risk_score": 5.0,
                "risk_factors": [],
                "citations": [],
                "ai_unavailable": True,
                "ai_error": str(exc),
                "attempted_models": attempted_models,
                "model_used": used_model,
            }

        try:
            raw = raw_text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
        except (json.JSONDecodeError, IndexError):
            result = {
                "reasoning_summary": raw_text,
                "assumptions": [],
                "confidence_score": 0.5,
                "risk_score": 5.0,
                "risk_factors": [],
                "citations": [],
            }

        result.setdefault("reasoning_summary", "")
        result.setdefault("assumptions", [])
        result.setdefault("confidence_score", 0.5)
        result.setdefault("risk_score", 5.0)
        result.setdefault("risk_factors", [])
        result.setdefault("citations", [])
        result.setdefault("ai_unavailable", False)
        result.setdefault("ai_error", None)
        result.setdefault("attempted_models", attempted_models)
        result.setdefault("model_used", used_model)

        # Keep scores consistent for downstream policy checks and UI labels.
        result["confidence_score"] = self._normalize_confidence(result.get("confidence_score"))
        result["risk_score"] = self._normalize_risk(result.get("risk_score"))

        return result
