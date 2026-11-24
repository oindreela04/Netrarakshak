"""One-click demo sign-in: only the seeded demo-tenant accounts, and never in production."""
from app.routers import auth as auth_router


def test_demo_accounts_listed(client):
    r = client.get("/api/auth/demo-accounts")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert {a["role"] for a in body["accounts"]} == {"technician", "ophthalmologist", "hospital_admin", "receptionist"}
    assert all("email" not in a for a in body["accounts"])


def test_demo_login_issues_session_for_role(client):
    r = client.post("/api/auth/demo-login", json={"role": "ophthalmologist"})
    assert r.status_code == 200, r.text
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["user"]["email"] == "doctor@aarogya.example"
    assert "review.write" in me["permissions"]


def test_demo_login_rejects_unknown_or_privileged_roles(client):
    assert client.post("/api/auth/demo-login", json={"role": "super_admin"}).status_code == 400
    assert client.post("/api/auth/demo-login", json={"role": "nobody"}).status_code == 400


def test_demo_login_disabled_in_production(client, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "environment", "production")
    assert client.post("/api/auth/demo-login", json={"role": "technician"}).status_code == 404
    assert client.get("/api/auth/demo-accounts").json() == {"enabled": False, "accounts": []}


def test_demo_login_can_be_switched_off(client, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "demo_login_enabled", False)
    assert client.post("/api/auth/demo-login", json={"role": "technician"}).status_code == 404
