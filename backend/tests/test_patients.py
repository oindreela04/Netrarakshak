from tests.conftest import new_patient


def test_register_search_edit_archive(client, H):
    p = new_patient(client, H["reception"], last_name="Searchable", has_hypertension=True, medications="Metformin 500mg")
    assert p["patient_code"].startswith("NR-AEH-")
    assert p["age"] >= 50 and p["consent_state"]["screening"] is True
    r = client.get("/api/patients?q=Searchable", headers=H["tech"]).json()
    assert r["total"] == 1
    assert client.get("/api/patients?q=Searchable&hypertension=false", headers=H["tech"]).json()["total"] == 0
    body = {k: p[k] for k in ("first_name", "last_name", "date_of_birth", "sex")} | {"phone": "+91 90000 00001", "has_diabetes": True}
    u = client.put(f"/api/patients/{p['id']}", headers=H["reception"], json=body)
    assert u.status_code == 200 and u.json()["phone"] == "+91 90000 00001"
    assert client.post(f"/api/patients/{p['id']}/archive", headers=H["admin"]).status_code == 200
    assert client.get("/api/patients?q=Searchable", headers=H["tech"]).json()["total"] == 0
    assert client.get("/api/patients?q=Searchable&archived=true", headers=H["tech"]).json()["total"] == 1
    assert client.put(f"/api/patients/{p['id']}", headers=H["reception"], json=body).status_code == 409
    assert client.post(f"/api/patients/{p['id']}/restore", headers=H["admin"]).status_code == 200


def test_validation(client, H):
    r = client.post("/api/patients", headers=H["reception"], json={"first_name": "SYNTHETIC", "date_of_birth": "2999-01-01"})
    assert r.status_code == 422


def test_screening_requires_consent(client, H):
    p = new_patient(client, H["reception"], consents=())
    r = client.post("/api/screenings", headers=H["tech"], json={"patient_id": p["id"]})
    assert r.status_code == 409 and "consent" in r.json()["detail"].lower()
    client.post(f"/api/patients/{p['id']}/consents", headers=H["reception"], json={"consent_type": "screening", "granted": True})
    assert client.post("/api/screenings", headers=H["tech"], json={"patient_id": p["id"]}).status_code == 201


def test_permanent_erasure(client, H):
    p = new_patient(client, H["reception"], last_name="Erase")
    assert client.delete(f"/api/patients/{p['id']}?confirm_code={p['patient_code']}", headers=H["admin"]).status_code == 409
    client.post(f"/api/patients/{p['id']}/archive", headers=H["admin"])
    assert client.delete(f"/api/patients/{p['id']}?confirm_code=WRONG", headers=H["admin"]).status_code == 400
    assert client.delete(f"/api/patients/{p['id']}?confirm_code={p['patient_code']}", headers=H["admin"]).status_code == 200
    assert client.get(f"/api/patients/{p['id']}", headers=H["admin"]).status_code == 404
