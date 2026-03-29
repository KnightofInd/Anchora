"""AI quality utilities for grounded decision generation."""

from __future__ import annotations

import re
from dataclasses import dataclass


_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _normalize_id(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    # Accept common model output wrappers such as "[uuid]" or "doc_id: uuid".
    uuid_match = _UUID_RE.search(raw)
    if uuid_match:
        return uuid_match.group(0).lower()

    bracket_match = re.search(r"\[([^\]]+)\]", raw)
    if bracket_match:
        raw = bracket_match.group(1)

    if ":" in raw:
        raw = raw.split(":", 1)[1]

    return raw.strip().lower()


@dataclass(slots=True)
class GroundingResult:
    score: float
    citation_coverage: float
    lexical_overlap: float
    passed: bool
    detail: str


class GroundingEvaluator:
    """Computes a lightweight groundedness score from context + retrieved docs."""

    @staticmethod
    def evaluate(
        *,
        reasoning_summary: str,
        context: str,
        retrieved_docs: list[dict[str, str]],
        citations: list[dict],
        min_score: float,
        require_at_least_one_citation: bool,
    ) -> GroundingResult:
        retrieved_by_id: dict[str, str] = {}
        retrieved_by_title: dict[str, str] = {}
        for doc in retrieved_docs:
            doc_id = _normalize_id(str(doc.get("id", "")))
            title = str(doc.get("title", "")).strip()
            if doc_id and title:
                retrieved_by_id[doc_id] = title
                retrieved_by_title[title.lower()] = doc_id

        valid_citation_ids: set[str] = set()
        for citation in citations:
            if not isinstance(citation, dict):
                continue
            raw_cited_id = (
                citation.get("document_id")
                or citation.get("id")
                or citation.get("source_document_id")
                or ""
            )
            cited_id = _normalize_id(str(raw_cited_id))
            if cited_id and cited_id in retrieved_by_id:
                valid_citation_ids.add(cited_id)
                continue

            cited_title = str(citation.get("document_title", "")).strip().lower()
            if cited_title and cited_title in retrieved_by_title:
                valid_citation_ids.add(retrieved_by_title[cited_title])

        titles = list(retrieved_by_id.values())
        citation_coverage = (
            len(valid_citation_ids) / len(retrieved_by_id)
            if retrieved_by_id
            else 0.0
        )

        source_tokens = _tokenize(context)
        source_tokens |= _tokenize(" ".join(titles))
        summary_tokens = _tokenize(reasoning_summary)
        lexical_overlap = (
            len(summary_tokens & source_tokens) / len(summary_tokens)
            if summary_tokens
            else 0.0
        )

        # Weighted blend: explicit citations matter most, lexical grounding second.
        score = round((0.7 * citation_coverage) + (0.3 * lexical_overlap), 4)

        passed = score >= min_score
        if require_at_least_one_citation and retrieved_by_id and not valid_citation_ids:
            passed = False

        if passed:
            detail = "Grounding gate passed."
        elif retrieved_by_id and not valid_citation_ids:
            detail = "Grounding gate failed: no retrieved document ID was cited."
        else:
            detail = f"Grounding gate failed: score {score:.3f} is below threshold {min_score:.3f}."

        return GroundingResult(
            score=score,
            citation_coverage=round(citation_coverage, 4),
            lexical_overlap=round(lexical_overlap, 4),
            passed=passed,
            detail=detail,
        )
