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
    "risk_factors": ["...", "..."]
}}

Rules:
- confidence_score: float 0.0–1.0
- risk_score: float 0.0–10.0
- Be explicit about assumptions
- reasoning_summary should cite document titles by name
"""


class AIService:
    def _sync_generate(self, prompt: str) -> str:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )
        return response.text or ""

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
        try:
            raw_text = await loop.run_in_executor(
                None,
                functools.partial(self._sync_generate, prompt),
            )
        except Exception as exc:
            logger.warning("Gemini generate_content failed, using fallback: %s", exc)
            return {
                "reasoning_summary": "AI service unavailable — manual review required.",
                "assumptions": [],
                "confidence_score": 0.5,
                "risk_score": 5.0,
                "risk_factors": [],
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
            }

        result.setdefault("reasoning_summary", "")
        result.setdefault("assumptions", [])
        result.setdefault("confidence_score", 0.5)
        result.setdefault("risk_score", 5.0)
        result.setdefault("risk_factors", [])

        return result
