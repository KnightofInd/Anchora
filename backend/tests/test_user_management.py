import uuid

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_list_roles_and_users(client: TestClient) -> None:
    headers = _auth_headers(client, "admin@anchora.dev", "Admin@1234")

    roles_response = client.get("/api/admin/roles", headers=headers)
    assert roles_response.status_code == 200, roles_response.text
    roles = roles_response.json()
    assert isinstance(roles, list)
    assert len(roles) > 0
    assert all("id" in role and "name" in role for role in roles)

    users_response = client.get("/api/admin/users", headers=headers)
    assert users_response.status_code == 200, users_response.text
    users = users_response.json()
    assert isinstance(users, list)
    assert len(users) > 0
    assert all("email" in user and "role_name" in user for user in users)


def test_non_admin_cannot_access_admin_endpoints(client: TestClient) -> None:
    admin_headers = _auth_headers(client, "admin@anchora.dev", "Admin@1234")
    roles_response = client.get("/api/admin/roles", headers=admin_headers)
    assert roles_response.status_code == 200, roles_response.text
    roles = roles_response.json()
    viewer_role = next((role for role in roles if role["name"] == "viewer"), None)
    assert viewer_role is not None

    unique_suffix = uuid.uuid4().hex[:8]
    create_payload = {
        "email": f"rbac.viewer.{unique_suffix}@anchora.dev",
        "full_name": "RBAC Viewer",
        "password": "ViewerTemp@123",
        "role_id": viewer_role["id"],
        "is_active": True,
    }
    create_response = client.post("/api/admin/users", headers=admin_headers, json=create_payload)
    assert create_response.status_code == 201, create_response.text

    viewer_headers = _auth_headers(client, create_payload["email"], create_payload["password"])
    response = client.get("/api/admin/users", headers=viewer_headers)
    assert response.status_code == 403


def test_admin_can_create_and_update_user(client: TestClient) -> None:
    headers = _auth_headers(client, "admin@anchora.dev", "Admin@1234")

    roles_response = client.get("/api/admin/roles", headers=headers)
    assert roles_response.status_code == 200, roles_response.text
    roles = roles_response.json()

    viewer_role = next((role for role in roles if role["name"] == "viewer"), None)
    auditor_role = next((role for role in roles if role["name"] == "auditor"), None)
    assert viewer_role is not None
    assert auditor_role is not None

    unique_suffix = uuid.uuid4().hex[:8]
    create_payload = {
        "email": f"test.user.{unique_suffix}@anchora.dev",
        "full_name": "Test User",
        "password": "TempPass@123",
        "role_id": viewer_role["id"],
        "is_active": True,
    }

    create_response = client.post("/api/admin/users", headers=headers, json=create_payload)
    assert create_response.status_code == 201, create_response.text
    created_user = create_response.json()
    assert created_user["email"] == create_payload["email"]
    assert created_user["role_name"] == "viewer"
    assert created_user["is_active"] is True

    update_payload = {
        "role_id": auditor_role["id"],
        "is_active": False,
    }
    update_response = client.patch(
        f"/api/admin/users/{created_user['id']}",
        headers=headers,
        json=update_payload,
    )
    assert update_response.status_code == 200, update_response.text
    updated_user = update_response.json()
    assert updated_user["role_name"] == "auditor"
    assert updated_user["is_active"] is False
