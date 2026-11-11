from app import audit
from app.database import SessionLocal
from tests.conftest import PW, new_patient, new_screening, upload


def _prepared(client, H, good_png):
    p = new_patient(client, H["tech"], last_name="Review")
    s = new_screening(client, H["tech"], p["id"])
    upload(client, H["tech"], s["id"], "right", good_png)
    upload(client, H["tech"], s["id"], "left", good_png)
    client.post(f"/api/screenings/{s['id']}/analyse", headers=H["tech"])  # model unavailable in this module
    return p, s


def test_review_sign_and_report(client, H, good_png):
    p, s = _prepared(client, H, good_png)
    sid = s["id"]
    queue = client.get("/api/reviews/queue", headers=H["doctor"]).json()
    assert any(q["id"] == sid for q in queue)

    # draft report before review is NOT approved
    draft = client.post(f"/api/reports/screening/{sid}", headers=H["tech"]).json()
    assert draft["review_status"].startswith("DRAFT")
    pdf = client.get(f"/api/reports/{draft['id']}/file", headers=H["reception"])
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # cannot accept an AI finding that does not exist
    bad = {"eye_findings": {"right": {"ai_decision": "accept", "final_grade": "no_dr"}}}
    assert client.put(f"/api/reviews/screening/{sid}", headers=H["doctor"], json=bad).status_code == 422

    review = {"eye_findings": {"right": {"ai_decision": "not_applicable", "final_grade": "moderate_npdr", "observations": "Synthetic test"},
                               "left": {"ai_decision": "not_applicable", "final_grade": "no_dr"}},
              "overall_impression": "Synthetic test case", "recommendations": "Refer to retina clinic",
              "referral_recommended": True, "referral_urgency": "soon", "follow_up_months": 3}
    r = client.put(f"/api/reviews/screening/{sid}", headers=H["doctor"], json=review)
    assert r.status_code == 200 and r.json()["status"] == "draft"

    # signing needs attestation + correct password
    assert client.post(f"/api/reviews/screening/{sid}/sign", headers=H["doctor"], json={"password": PW, "attestation": False}).status_code == 422
    assert client.post(f"/api/reviews/screening/{sid}/sign", headers=H["doctor"], json={"password": "wrong", "attestation": True}).status_code == 401
    signed = client.post(f"/api/reviews/screening/{sid}/sign", headers=H["doctor"], json={"password": PW, "attestation": True})
    assert signed.status_code == 200 and signed.json()["status"] == "signed" and len(signed.json()["signature_hash"]) == 64

    # signed screening is locked
    assert upload(client, H["tech"], sid, "right", good_png).status_code == 409
    assert client.put(f"/api/reviews/screening/{sid}", headers=H["doctor"], json=review).status_code == 409

    final = client.post(f"/api/reports/screening/{sid}", headers=H["doctor"]).json()
    assert final["review_status"] == "CLINICIAN APPROVED"
    pdf = client.get(f"/api/reports/{final['id']}/file?download=true", headers=H["doctor"])
    assert pdf.content.startswith(b"%PDF") and "attachment" in pdf.headers["content-disposition"]
    assert len(pdf.content) > 20_000  # includes embedded retinal images

    # patient history shows both reports; screening status is reported
    d = client.get(f"/api/patients/{p['id']}", headers=H["reception"]).json()
    assert len(d["reports"]) == 2 and d["screenings"][0]["status"] == "reported"
    # dashboard reflects the signed screening
    dash = client.get("/api/analytics/dashboard", headers=H["admin"]).json()
    assert dash["totals"]["signed"] >= 1 and dash["clinician_grades"].get("moderate_npdr", 0) >= 1


def test_recapture_request(client, H, good_png):
    _, s = _prepared(client, H, good_png)
    r = client.post(f"/api/reviews/screening/{s['id']}/request-recapture", headers=H["doctor"],
                    json={"reason": "Media haze", "eyes": ["right"]})
    assert r.status_code == 200
    assert client.get(f"/api/screenings/{s['id']}", headers=H["tech"]).json()["status"] == "recapture_requested"
    rep = client.post(f"/api/reports/screening/{s['id']}", headers=H["tech"]).json()
    assert rep["review_status"].startswith("RECAPTURE")
    # technician can upload the new photograph
    assert upload(client, H["tech"], s["id"], "right", good_png).status_code == 201


def test_audit_chain_intact(client, H):
    db = SessionLocal()
    try:
        assert audit.verify_chain(db)["valid"] is True
    finally:
        db.close()
    assert client.get("/api/platform/audit/verify", headers=H["super"]).json()["valid"] is True


def test_platform_billing(client, H):
    hs = client.get("/api/platform/hospitals", headers=H["super"]).json()
    sunrise = next(h for h in hs if h["code"] == "SVC")
    inv = client.post(f"/api/platform/hospitals/{sunrise['id']}/invoices", headers=H["super"]).json()
    assert inv["total_inr"] == round(14999 * 1.18)
    assert client.post(f"/api/platform/invoices/{inv['id']}/paid", headers=H["super"], json={"reference": "NEFT-TEST"}).status_code == 200
    sub = client.get("/api/admin/subscription", headers=H["other_admin"]).json()
    assert sub["invoices"][0]["status"] == "paid" and sub["plan"]["code"] == "STARTER"
    # suspending the licence blocks new screenings
    client.put(f"/api/platform/hospitals/{sunrise['id']}", headers=H["super"],
               json={"plan_code": "STARTER", "billing_cycle": "monthly", "licence_status": "suspended", "is_active": True})
    pats = client.get("/api/patients", headers=H["other_admin"]).json()["items"]
    r = client.post("/api/screenings", headers=H["other_tech"], json={"patient_id": pats[0]["id"]})
    assert r.status_code == 402
    client.put(f"/api/platform/hospitals/{sunrise['id']}", headers=H["super"],
               json={"plan_code": "STARTER", "billing_cycle": "monthly", "licence_status": "active", "is_active": True})


def test_public_enquiry(client):
    r = client.post("/api/public/enquiries", json={"name": "Test Person", "organisation": "Test Org", "email": "t@example.com",
                                                    "message": "Demo please", "kind": "demo"})
    assert r.status_code == 201
    assert len(client.get("/api/public/plans").json()) == 3
