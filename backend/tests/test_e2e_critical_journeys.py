import pytest
from fastapi.testclient import TestClient

from app.core.policy_engine.interface import PolicyResult
from app.core.policy_engine.evaluator import LocalPolicyEvaluator
from app.config.settings import settings
from app.services.ai_service import AIService
from app.services.embedding import EmbeddingService

ADMIN_EMAIL = "admin@anchora.dev"
ADMIN_PASSWORD = "Admin@1234"


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def patch_ai_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ai_generate(self, title: str, description: str, context: str, document_summaries: list[dict]) -> dict:
        first_doc = document_summaries[0] if document_summaries else {"id": "", "title": ""}
        return {
            "reasoning_summary": "Policy-aligned context review recommends approval with controls.",
            "assumptions": ["No hidden constraints."],
            "confidence_score": 0.73,
            "risk_score": 4.2,
            "risk_factors": ["Operational risk"],
            "citations": [
                {
                    "document_id": first_doc.get("id", ""),
                    "document_title": first_doc.get("title", ""),
                    "evidence_quote": "policy-aligned review",
                }
            ],
        }

    async def fake_embedding(self, text: str) -> list[float]:
        raise RuntimeError("Force deterministic fallback retrieval in tests")

    async def fake_policy_eval(self, payload: dict) -> PolicyResult:
        return PolicyResult(
            allowed=True,
            matched_policies=["test-allow"],
            violations=[],
            requires_escalation=False,
            notes="test override",
        )

    monkeypatch.setattr(AIService, "generate_decision_recommendation", fake_ai_generate)
    monkeypatch.setattr(EmbeddingService, "generate", fake_embedding)
    monkeypatch.setattr(LocalPolicyEvaluator, "evaluate", fake_policy_eval)
    monkeypatch.setattr(settings, "AI_GROUNDING_GATE_ENABLED", False)


def test_critical_journey_decision_create_with_idempotency(client: TestClient) -> None:
    headers = _auth_headers(client)
    payload = {
        "title": "Phase4 E2E Decision",
        "description": "Regression flow",
        "context": "budget approval and security control context",
    }

    first = client.post(
        "/api/decisions/",
        headers={**headers, "Idempotency-Key": "e2e-decision-idem-1"},
        json=payload,
    )
    assert first.status_code == 201, first.text
    created = first.json()
    assert "quality_snapshot" in created
    assert "policy_snapshot" in created

    second = client.post(
        "/api/decisions/",
        headers={**headers, "Idempotency-Key": "e2e-decision-idem-1"},
        json=payload,
    )
    assert second.status_code == 201, second.text
    assert second.headers.get("Idempotent-Replayed") == "true"


def test_critical_journey_non_draft_workflow_guard(client: TestClient) -> None:
    headers = _auth_headers(client)

    create = client.post(
        "/api/decisions/",
        headers=headers,
        json={
            "title": "Phase4 Guard Decision",
            "description": "guard flow",
            "context": "policy context with operations",
        },
    )
    assert create.status_code == 201, create.text
    decision = create.json()

    approve = client.patch(
        f"/api/decisions/{decision['id']}/status",
        headers=headers,
        json={"status": "approved", "notes": "e2e promote"},
    )
    assert approve.status_code == 200, approve.text

    start = client.post(
        "/api/workflows/",
        headers=headers,
        json={"decision_id": decision["id"]},
    )
    assert start.status_code == 409
    body = start.json()
    assert body["error"]["code"] == "HTTP_409"


def test_ops_slo_endpoint_available(client: TestClient) -> None:
    headers = _auth_headers(client)
    slo = client.get("/api/ops/slo", headers=headers)
    assert slo.status_code == 200, slo.text
    data = slo.json()
    assert "error_rate" in data
    assert "p95_latency_ms" in data
    assert "targets" in data
