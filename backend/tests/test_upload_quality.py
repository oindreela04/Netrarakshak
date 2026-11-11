import cv2
import numpy as np

from app.services.quality import assess_quality
from app.services.synthetic_fundus import encode, make_synthetic_fundus
from tests.conftest import new_patient, new_screening, upload


def test_quality_unit_cases(good_png, blurry_png):
    assert assess_quality(good_png)["verdict"] == "acceptable"
    q = assess_quality(blurry_png)
    assert q["verdict"] == "recapture_required"
    assert any(c["key"] == "blur" and c["status"] == "fail" for c in q["checks"])
    dark = assess_quality(encode(make_synthetic_fundus(1024, seed=3, brightness=0.15)))
    assert dark["verdict"] == "recapture_required"
    assert any(c["key"] == "brightness" and c["status"] == "fail" for c in dark["checks"])
    small = assess_quality(encode(cv2.resize(make_synthetic_fundus(1024, seed=4), (300, 300))))
    assert any(c["key"] == "resolution" and c["status"] == "fail" for c in small["checks"])
    # a non-fundus photograph (uniform blue/grey scene) must be rejected
    scene = np.full((900, 1200, 3), (180, 140, 90), np.uint8)
    cv2.putText(scene, "NOT A FUNDUS", (100, 450), cv2.FONT_HERSHEY_SIMPLEX, 4, (20, 20, 20), 8)
    assert assess_quality(encode(scene))["verdict"] == "recapture_required"


def test_upload_formats_and_replacement(client, H, good_png, blurry_png):
    p = new_patient(client, H["tech"])
    s = new_screening(client, H["tech"], p["id"])
    sid = s["id"]
    r = upload(client, H["tech"], sid, "right", good_png)
    assert r.status_code == 201 and r.json()["quality_verdict"] == "acceptable"
    assert r.json()["metadata"]["format"] == "image/png"
    # JPEG and TIFF are accepted
    img = make_synthetic_fundus(1024, seed=21, eye="left")
    ok, jpg = cv2.imencode(".jpg", img)
    assert upload(client, H["tech"], sid, "left", jpg.tobytes(), "left.jpg").status_code == 201
    ok, tif = cv2.imencode(".tiff", img)
    r = upload(client, H["tech"], sid, "left", tif.tobytes(), "left.tiff")
    assert r.status_code == 201 and r.json()["content_type"] == "image/tiff"
    # TIFF served as PNG rendition for browsers
    f = client.get(f"/api/screenings/{sid}/images/{r.json()['id']}/file", headers=H["doctor"])
    assert f.status_code == 200 and f.headers["content-type"] == "image/png"
    # replacement keeps history
    d = client.get(f"/api/screenings/{sid}", headers=H["tech"]).json()
    assert len(d["images"]) == 2 and len(d["replaced_images"]) == 1
    assert d["status"] == "quality_checked"
    # rejected types
    assert upload(client, H["tech"], sid, "right", b"%PDF-1.4 fake", "x.pdf").status_code == 415
    assert upload(client, H["tech"], sid, "right", b"not an image at all", "x.png").status_code == 415
    assert upload(client, H["tech"], sid, "middle", good_png).status_code == 422
    # blurry image is stored but flagged
    r = upload(client, H["tech"], sid, "right", blurry_png)
    assert r.json()["quality_verdict"] == "recapture_required"
    assert "Recapture required" in r.json()["quality"]["summary"]


def test_images_are_encrypted_at_rest(client, H, good_png):
    from app.config import get_settings
    from pathlib import Path
    p = new_patient(client, H["tech"])
    s = new_screening(client, H["tech"], p["id"])
    img = upload(client, H["tech"], s["id"], "right", good_png).json()
    files = list(Path(get_settings().local_storage_dir).rglob(f"{img['id']}*"))
    assert files and not files[0].read_bytes().startswith(b"\x89PNG")
    served = client.get(f"/api/screenings/{s['id']}/images/{img['id']}/file", headers=H["doctor"]).content
    assert served == good_png
