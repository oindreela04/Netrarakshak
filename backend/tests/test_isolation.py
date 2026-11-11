"""Hospital-level data isolation: one tenant must never read or modify another tenant's records."""
from tests.conftest import new_patient, new_screening, upload


def test_cross_tenant_access_denied(client, H, good_png):
    p = new_patient(client, H["admin"], last_name="IsolationA")
    s = new_screening(client, H["tech"], p["id"])
    img = upload(client, H["tech"], s["id"], "right", good_png).json()
    rep = client.post(f"/api/reports/screening/{s['id']}", headers=H["tech"]).json()

    o = H["other_admin"]
    assert client.get(f"/api/patients/{p['id']}", headers=o).status_code == 404
    assert client.put(f"/api/patients/{p['id']}", headers=o, json={"first_name": "x", "date_of_birth": "1970-01-01"}).status_code == 404
    assert client.post(f"/api/patients/{p['id']}/archive", headers=o).status_code == 404
    assert client.get(f"/api/screenings/{s['id']}", headers=o).status_code == 404
    assert client.get(f"/api/screenings/{s['id']}/images/{img['id']}/file", headers=o).status_code == 404
    assert upload(client, H["other_tech"], s["id"], "left", good_png).status_code == 404
    assert client.post(f"/api/screenings", headers=H["other_tech"], json={"patient_id": p["id"]}).status_code == 404
    assert client.get(f"/api/reports/{rep['id']}/file", headers=o).status_code == 404
    assert client.post(f"/api/reports/screening/{s['id']}", headers=H["other_tech"]).status_code == 404

    listing = client.get("/api/patients?q=IsolationA", headers=o).json()
    assert listing["total"] == 0
    assert all(i["id"] != s["id"] for i in client.get("/api/screenings", headers=o).json()["items"])
    assert all(i["id"] != rep["id"] for i in client.get("/api/reports", headers=o).json()["items"])
    # audit logs are tenant-scoped as well
    assert all(a["entity_id"] != p["id"] for a in client.get("/api/admin/audit?page_size=500", headers=o).json()["items"])
