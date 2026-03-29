"""Retrieval benchmark helpers used by test and CI quality gates."""

from __future__ import annotations

import re
from dataclasses import dataclass


_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


@dataclass(slots=True)
class RetrievalDoc:
    doc_id: str
    text: str


@dataclass(slots=True)
class RetrievalCase:
    name: str
    query: str
    expected_doc_ids: set[str]


@dataclass(slots=True)
class RetrievalBenchmarkResult:
    precision_at_k: float
    recall_at_k: float
    passed: bool


class LexicalRetriever:
    """Deterministic retriever used for benchmark reproducibility."""

    def __init__(self, docs: list[RetrievalDoc]):
        self.docs = docs

    def retrieve(self, query: str, k: int) -> list[str]:
        q = _tokenize(query)
        scored: list[tuple[int, str]] = []
        for doc in self.docs:
            overlap = len(q & _tokenize(doc.text))
            scored.append((overlap, doc.doc_id))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc_id for score, doc_id in scored[:k] if score > 0]


def run_benchmark(
    *,
    retriever: LexicalRetriever,
    cases: list[RetrievalCase],
    k: int,
    min_precision: float,
) -> RetrievalBenchmarkResult:
    total_hits = 0
    total_pred = 0
    total_expected = 0

    for case in cases:
        predicted = set(retriever.retrieve(case.query, k))
        expected = case.expected_doc_ids
        hits = len(predicted & expected)

        total_hits += hits
        total_pred += len(predicted)
        total_expected += len(expected)

    precision = (total_hits / total_pred) if total_pred else 0.0
    recall = (total_hits / total_expected) if total_expected else 0.0

    return RetrievalBenchmarkResult(
        precision_at_k=round(precision, 4),
        recall_at_k=round(recall, 4),
        passed=precision >= min_precision,
    )
