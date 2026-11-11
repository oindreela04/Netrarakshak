"""AI pipeline tests.

A tiny model is trained here on SYNTHETIC images purely to exercise the real code path (preprocessing → forward
pass → calibration → Grad-CAM → storage). Its outputs have no clinical meaning and the registry blocks such
models from patient use unless ALLOW_NONCLINICAL_TEST_MODELS is explicitly enabled (tests only).
"""
import json

import numpy as np
import pytest

from ai import registry
from app.config import get_settings
from app.services.quality import decode_image
from tests.conftest import new_patient, new_screening, upload

settings = get_settings()


@pytest.fixture(scope="module")
def smoke_model(tmp_path_factory):
    import subprocess, sys
    d = tmp_path_factory.mktemp("synds")
    subprocess.run([sys.executable, "scripts/make_synthetic_dataset.py", "--out", str(d), "--n", "40", "--size", "256"], check=True)
    from ai.modules.diabetic_retinopathy import train
    train.main(["--labels", str(d / "labels.csv"), "--images", str(d / "images"), "--dataset-name", "SYNTHETIC",
                "--dataset-licence", "generated", "--synthetic", "--no-pretrained", "--size", "64", "--epochs", "1",
                "--batch-size", "8", "--workers", "0", "--work-dir", str(d / "runs"), "--registry", settings.model_registry_dir,
                "--version", "test-smoke"])
    registry.clear_cache()
    yield
    (registry.module_dir("diabetic_retinopathy") / "ACTIVE").unlink(missing_ok=True)
    registry.clear_cache()


def _screen(client, H, png, **pk):
    p = new_patient(client, H["tech"], **pk)
    s = new_screening(client, H["tech"], p["id"])
    upload(client, H["tech"], s["id"], "right", png)
    return p, s


def test_model_unavailable_routes_to_human(client, H, good_png):
    (registry.module_dir("diabetic_retinopathy") / "ACTIVE").unlink(missing_ok=True)
    _, s = _screen(client, H, good_png)
    r = client.post(f"/api/screenings/{s['id']}/analyse", headers=H["tech"]).json()["results"][0]
    assert r["status"] == "model_unavailable"
    assert "HUMAN REVIEW REQUIRED" in r["display_verdict"]
    assert r["predicted_label"] == "" and r["probabilities"] == {} and r["confidence"] is None


def test_synthetic_model_blocked_by_default(client, H, good_png, smoke_model, monkeypatch):
    monkeypatch.setattr(settings, "allow_nonclinical_test_models", False)
    info = registry.availability("diabetic_retinopathy")
    assert info["available"] is False and "synthetic" in info["reason"].lower()
    _, s = _screen(client, H, good_png)
    r = client.post(f"/api/screenings/{s['id']}/analyse", headers=H["tech"]).json()["results"][0]
    assert r["status"] == "model_unavailable"


def test_real_inference_and_gradcam(client, H, good_png, smoke_model, monkeypatch):
    monkeypatch.setattr(settings, "allow_nonclinical_test_models", True)
    _, s = _screen(client, H, good_png)
    r = client.post(f"/api/screenings/{s['id']}/analyse", headers=H["tech"]).json()["results"][0]
    assert r["status"] == "completed" and r["model_version"] == "test-smoke"
    probs = np.array(list(r["probabilities"].values()))
    assert len(probs) == 5 and abs(probs.sum() - 1) < 1e-4
    assert r["confidence"] == pytest.approx(probs.max(), abs=1e-6)
    assert r["has_gradcam"]
    for kind in ("overlay", "heatmap"):
        g = client.get(f"/api/screenings/{s['id']}/ai/{r['id']}/{kind}", headers=H["doctor"])
        assert g.status_code == 200 and decode_image(g.content).shape == (512, 512, 3)
    # deterministic: the same photograph gives the same output (no randomness)
    r2 = client.post(f"/api/screenings/{s['id']}/analyse", headers=H["tech"]).json()["results"][0]
    assert r2["probabilities"] == r["probabilities"]
    # direct predictor matches API output
    pred = registry.get_predictor("diabetic_retinopathy")
    direct = pred.predict(decode_image(good_png), 0.6, 0.75)
    assert direct["probabilities"] == r["probabilities"]


def test_uncertainty_forces_inconclusive(client, H, good_png, smoke_model, monkeypatch):
    monkeypatch.setattr(settings, "allow_nonclinical_test_models", True)
    monkeypatch.setattr(settings, "uncertainty_confidence_threshold", 0.999)
    _, s = _screen(client, H, good_png)
    r = client.post(f"/api/screenings/{s['id']}/analyse", headers=H["tech"]).json()["results"][0]
    assert r["status"] == "completed" and r["is_uncertain"]
    assert r["display_verdict"] == "INCONCLUSIVE — HUMAN REVIEW REQUIRED"


def test_poor_quality_and_missing_consent_skip_inference(client, H, good_png, blurry_png, smoke_model, monkeypatch):
    monkeypatch.setattr(settings, "allow_nonclinical_test_models", True)
    _, s = _screen(client, H, blurry_png)
    r = client.post(f"/api/screenings/{s['id']}/analyse", headers=H["tech"]).json()["results"][0]
    assert r["status"] == "quality_rejected" and r["confidence"] is None
    _, s = _screen(client, H, good_png, consents=("screening",))
    r = client.post(f"/api/screenings/{s['id']}/analyse", headers=H["tech"]).json()["results"][0]
    assert r["status"] == "consent_missing" and r["confidence"] is None


def test_tampered_weights_blocked(smoke_model, monkeypatch):
    monkeypatch.setattr(settings, "allow_nonclinical_test_models", True)
    vdir = registry.module_dir("diabetic_retinopathy") / "test-smoke"
    card = json.loads((vdir / "model_card.json").read_text())
    orig = card["weights_sha256"]
    card["weights_sha256"] = "0" * 64
    (vdir / "model_card.json").write_text(json.dumps(card))
    try:
        assert registry.availability("diabetic_retinopathy")["available"] is False
    finally:
        card["weights_sha256"] = orig
        (vdir / "model_card.json").write_text(json.dumps(card))


def test_model_card_metrics_are_computed(smoke_model):
    card = registry.read_card("diabetic_retinopathy")
    m = card["evaluation"]["test_metrics"]
    for k in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "quadratic_weighted_kappa", "confusion_matrix", "referable"):
        assert k in m
    assert sum(map(sum, m["confusion_matrix"])) == m["n"] == card["training_data"]["split_sizes"]["test"]
    assert card["training_data"]["synthetic"] is True
    assert "NEVER USE ON PATIENTS" in card["clinical_use_status"]
