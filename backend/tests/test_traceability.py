"""Phase 3 regression tests for the already delivered hardening work.

Coverage targets:
1. Phase 1 API contracts (pagination + validation envelope)
2. Phase 2 policy snapshot persistence exposure
3. Phase 2 workflow guard (non-draft decision cannot start workflow)
"""

import pytest
from fastapi.testclient import TestClient

ADMIN_EMAIL = "admin@anchora.dev"
ADMIN_PASSWORD = "Admin@1234"


def _auth_headers(client: TestClient) -> dict[str, str]:
    """Login using seeded admin credentials and return bearer auth headers."""
    login = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint_is_up(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_decisions_list_supports_phase1_pagination_and_phase2_snapshot(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.get(
        "/api/decisions/?limit=5&offset=0&sort_by=created_at&sort_order=desc",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    decisions = response.json()
    assert isinstance(decisions, list)
    assert len(decisions) <= 5

    # If seeded records exist, each record should expose policy_snapshot.
    if decisions:
        first = decisions[0]
        assert "policy_snapshot" in first
        assert isinstance(first["policy_snapshot"], dict)


def test_validation_errors_use_normalized_envelope(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.get("/api/decisions/?limit=0", headers=headers)
    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["detail"], list)


def test_phase2_guard_blocks_workflow_start_for_non_draft_decision(client: TestClient) -> None:
    headers = _auth_headers(client)

    dec_resp = client.get("/api/decisions/?limit=20", headers=headers)
    assert dec_resp.status_code == 200, dec_resp.text
    decisions = dec_resp.json()

    non_draft = next((d for d in decisions if d.get("status") != "draft"), None)
    if non_draft is None:
        pytest.skip("No non-draft decision available in seed data for guard test.")

    start_resp = client.post(
        "/api/workflows/",
        headers=headers,
        json={"decision_id": non_draft["id"]},
    )
    assert start_resp.status_code == 409
    body = start_resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "HTTP_409"
