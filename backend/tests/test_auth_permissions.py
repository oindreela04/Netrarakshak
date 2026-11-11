from tests.conftest import PW, login, new_patient, new_screening, upload


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_login_and_me(client, H):
    r = client.get("/api/auth/me", headers=H["doctor"])
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "ophthalmologist"
    assert "review.sign" in r.json()["permissions"]


def test_bad_password_generic_error(client):
    r = client.post("/api/auth/login", json={"email": "doctor@aarogya.example", "password": "nope"})
    assert r.status_code == 401 and r.json()["detail"] == "Incorrect email or password"
    r = client.post("/api/auth/login", json={"email": "nobody@x.example", "password": "nope"})
    assert r.status_code == 401 and r.json()["detail"] == "Incorrect email or password"


def test_unauthenticated_rejected(client):
    assert client.get("/api/patients").status_code == 401
    assert client.get("/api/patients", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_lockout_after_failed_attempts(client, H):
    r = client.post("/api/admin/users", headers=H["admin"], json={"email": "lock@aarogya.example", "full_name": "Lock Test",
                                                                  "role": "receptionist", "temporary_password": "Lock-Test-123!"})
    assert r.status_code == 201, r.text
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "lock@aarogya.example", "password": "wrong"})
    r = client.post("/api/auth/login", json={"email": "lock@aarogya.example", "password": "Lock-Test-123!"})
    assert r.status_code == 423


def test_refresh_rotation_and_logout(client):
    r = client.post("/api/auth/login", json={"email": "tech@aarogya.example", "password": PW}).json()
    r2 = client.post("/api/auth/refresh", json={"refresh_token": r["refresh_token"]})
    assert r2.status_code == 200
    # old refresh token is single-use
    assert client.post("/api/auth/refresh", json={"refresh_token": r["refresh_token"]}).status_code == 401
    # old access token's session revoked by rotation
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {r['access_token']}"}).status_code == 401
    h = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_password_policy(client):
    h = login(client, "reception@aarogya.example")
    r = client.post("/api/auth/change-password", headers=h, json={"current_password": PW, "new_password": "short"})
    assert r.status_code == 422


def test_role_permissions(client, H, good_png):
    p = new_patient(client, H["reception"])  # receptionist can register
    s = new_screening(client, H["tech"], p["id"])
    # receptionist: no image upload, no AI, no image viewing, no review
    assert upload(client, H["reception"], s["id"], "right", good_png).status_code == 403
    assert client.post(f"/api/screenings/{s['id']}/analyse", headers=H["reception"]).status_code == 403
    assert client.put(f"/api/reviews/screening/{s['id']}", headers=H["reception"], json={}).status_code == 403
    # technician cannot review/sign or manage users
    assert client.put(f"/api/reviews/screening/{s['id']}", headers=H["tech"], json={}).status_code == 403
    assert client.post(f"/api/reviews/screening/{s['id']}/sign", headers=H["tech"], json={"password": PW, "attestation": True}).status_code == 403
    assert client.get("/api/admin/users", headers=H["tech"]).status_code == 403
    # doctor cannot manage users or archive
    assert client.get("/api/admin/users", headers=H["doctor"]).status_code == 403
    assert client.post(f"/api/patients/{p['id']}/archive", headers=H["doctor"]).status_code == 403
    # hospital admin cannot reach platform endpoints
    assert client.get("/api/platform/hospitals", headers=H["admin"]).status_code == 403


def test_super_admin_has_no_patient_access(client, H):
    assert client.get("/api/patients", headers=H["super"]).status_code == 403
    assert client.get("/api/platform/hospitals", headers=H["super"]).status_code == 200


def test_plan_user_limit(client, H):
    # Sunrise is on STARTER (max 5 users); it has 4 seeded staff
    ok = client.post("/api/admin/users", headers=H["other_admin"], json={"email": "five@sunrise.example", "full_name": "Fifth",
                                                                         "role": "technician", "temporary_password": "Fifth-User-123!"})
    assert ok.status_code == 201
    over = client.post("/api/admin/users", headers=H["other_admin"], json={"email": "six@sunrise.example", "full_name": "Sixth",
                                                                           "role": "technician", "temporary_password": "Sixth-User-123!"})
    assert over.status_code == 402
