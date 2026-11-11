"""Test fixtures. Uses an isolated SQLite DB, temp encrypted storage and a temp model registry.
All patients and images here are SYNTHETIC. Test results say nothing about clinical performance."""
import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="nr_test_")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_TMP}/test.db",
    "LOCAL_STORAGE_DIR": f"{_TMP}/storage",
    "MODEL_REGISTRY_DIR": f"{_TMP}/registry",
    "STORAGE_ENCRYPTION_KEY": "",
    "JWT_SECRET": "test-secret-0123456789-0123456789-abcdef",
    "ENVIRONMENT": "test",
    "ALLOW_NONCLINICAL_TEST_MODELS": "false",
})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.synthetic_fundus import encode, make_synthetic_fundus  # noqa: E402

PW = "Demo@NetraRakshak2026"


@pytest.fixture(scope="session")
def client():
    from scripts import seed
    sys.argv = ["seed"]
    seed.main()
    with TestClient(app) as c:
        yield c


def login(client, email, pw=PW):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def H(client):
    return {k: login(client, f"{k}@aarogya.example") for k in ("admin", "doctor", "tech", "reception")} | {
        "other_admin": login(client, "admin@sunrise.example"), "other_tech": login(client, "tech@sunrise.example"),
        "super": login(client, "superadmin@netrarakshak.in")}


@pytest.fixture(scope="session")
def good_png():
    return encode(make_synthetic_fundus(1024, seed=11, lesions=8))


@pytest.fixture(scope="session")
def blurry_png():
    return encode(make_synthetic_fundus(1024, seed=12, blur=9))


def new_patient(client, headers, consents=("screening", "ai_analysis", "data_storage"), **kw):
    body = {"first_name": "SYNTHETIC", "last_name": kw.pop("last_name", "Test"), "date_of_birth": "1970-01-01",
            "sex": "female", "has_diabetes": True, "is_synthetic": True,
            "consents": [{"consent_type": c, "granted": True} for c in consents], **kw}
    r = client.post("/api/patients", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def new_screening(client, headers, patient_id):
    r = client.post("/api/screenings", json={"patient_id": patient_id, "camera_device": "TEST-CAMERA"}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def upload(client, headers, sid, eye, data, name="eye.png"):
    return client.post(f"/api/screenings/{sid}/images/{eye}", files={"file": (name, data, "image/png")}, headers=headers)
