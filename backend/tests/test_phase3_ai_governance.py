from app.config.settings import settings
from app.core.ai_quality import GroundingEvaluator
from app.core.retrieval_benchmark import (
    LexicalRetriever,
    RetrievalCase,
    RetrievalDoc,
    run_benchmark,
)


def test_grounding_evaluator_passes_when_citation_exists() -> None:
    result = GroundingEvaluator.evaluate(
        reasoning_summary="Based on Information Security Policy and risk factors, approve with controls.",
        context="We are patching production servers under security process.",
        retrieved_docs=[
            {"id": "p11", "title": "Information Security Policy"},
            {"id": "p14", "title": "Incident Response Policy"},
        ],
        citations=[
            {
                "document_id": "p11",
                "document_title": "Information Security Policy",
                "evidence_quote": "critical vulnerability remediation",
            }
        ],
        min_score=0.2,
        require_at_least_one_citation=True,
    )
    assert result.passed is True
    assert result.citation_coverage > 0


def test_grounding_evaluator_fails_when_no_valid_citation_exists() -> None:
    result = GroundingEvaluator.evaluate(
        reasoning_summary="Proceed based on general confidence only.",
        context="Policy aware decision.",
        retrieved_docs=[{"id": "p11", "title": "Information Security Policy"}],
        citations=[{"document_id": "unknown-doc", "document_title": "Unknown"}],
        min_score=0.2,
        require_at_least_one_citation=True,
    )
    assert result.passed is False
    assert "no retrieved document id was cited" in result.detail.lower()


def test_grounding_evaluator_accepts_bracketed_uuid_citation() -> None:
    doc_id = "9f5d73c8-8ac0-41fd-a6ea-6395a89cd51b"
    result = GroundingEvaluator.evaluate(
        reasoning_summary="Approve with controls aligned to policy.",
        context="Security tooling procurement decision.",
        retrieved_docs=[{"id": doc_id, "title": "Information Security Policy"}],
        citations=[
            {
                "document_id": f"[{doc_id}]",
                "document_title": "Information Security Policy",
            }
        ],
        min_score=0.2,
        require_at_least_one_citation=True,
    )

    assert result.passed is True
    assert result.citation_coverage == 1.0


def test_grounding_evaluator_accepts_title_only_citation() -> None:
    result = GroundingEvaluator.evaluate(
        reasoning_summary="Approve with controls aligned to Information Security Policy.",
        context="Security tooling procurement decision.",
        retrieved_docs=[{"id": "p11", "title": "Information Security Policy"}],
        citations=[
            {
                "document_title": "Information Security Policy",
                "evidence_quote": "MFA is mandatory for production access.",
            }
        ],
        min_score=0.2,
        require_at_least_one_citation=True,
    )

    assert result.passed is True
    assert result.citation_coverage == 1.0


def test_retrieval_benchmark_meets_threshold() -> None:
    docs = [
        RetrievalDoc(doc_id="p2", text="Delegation of Authority matrix financial approval thresholds"),
        RetrievalDoc(doc_id="p11", text="Information Security policy critical vulnerability remediation"),
        RetrievalDoc(doc_id="p16", text="Anti-bribery corruption policy due diligence government officials"),
    ]
    cases = [
        RetrievalCase(
            name="authority-threshold",
            query="who can approve high value expenditure",
            expected_doc_ids={"p2"},
        ),
        RetrievalCase(
            name="security-patching",
            query="critical vulnerability remediation timeline",
            expected_doc_ids={"p11"},
        ),
        RetrievalCase(
            name="anti-bribery",
            query="government intermediary due diligence",
            expected_doc_ids={"p16"},
        ),
    ]

    benchmark = run_benchmark(
        retriever=LexicalRetriever(docs),
        cases=cases,
        k=2,
        min_precision=settings.RETRIEVAL_BENCHMARK_MIN_PRECISION,
    )

    assert benchmark.passed is True
    assert benchmark.precision_at_k >= settings.RETRIEVAL_BENCHMARK_MIN_PRECISION
