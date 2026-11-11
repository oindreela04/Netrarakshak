"""Orchestrates AI screening for a session: quality gate → consent gate → model availability → real inference."""
import cv2
from sqlalchemy.orm import Session

from ai import registry
from ai.modules.diabetic_retinopathy.infer import INCONCLUSIVE

from ..config import get_settings
from ..models import AIResult, Screening
from ..serializers import active_consents
from ..storage import get_storage
from .quality import decode_image

settings = get_settings()
MODULE = "diabetic_retinopathy"


def _png(rgb) -> bytes:
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    assert ok
    return buf.tobytes()


def run_screening_analysis(db: Session, s: Screening) -> list[AIResult]:
    store = get_storage()
    consent_ok = active_consents(s.patient).get("ai_analysis", False)
    results = []
    for img in [i for i in s.images if i.is_current]:
        base = dict(screening_id=s.id, hospital_id=s.hospital_id, image_id=img.id, eye=img.eye, module=MODULE)
        if not consent_ok:
            r = AIResult(**base, status="consent_missing", display_verdict=INCONCLUSIVE,
                         explanation="Patient has not granted (or has withdrawn) consent for AI analysis. No AI processing was performed.")
        elif img.quality_verdict != "acceptable":
            r = AIResult(**base, status="quality_rejected", display_verdict=INCONCLUSIVE,
                         explanation=f"AI analysis not performed: image quality is '{img.quality_verdict.replace('_', ' ')}'. "
                                     + (img.quality or {}).get("summary", ""))
        else:
            try:
                predictor = registry.get_predictor(MODULE)
            except registry.ModelUnavailable as e:
                r = AIResult(**base, status="model_unavailable", display_verdict="AI MODEL NOT AVAILABLE — HUMAN REVIEW REQUIRED",
                             explanation=f"No AI result was produced. {e}")
            else:
                try:
                    bgr = decode_image(store.get(img.storage_key))
                    out = predictor.predict(bgr, settings.uncertainty_confidence_threshold, settings.uncertainty_entropy_threshold)
                except Exception as e:  # inference failure must never produce a finding
                    r = AIResult(**base, status="error", display_verdict=INCONCLUSIVE,
                                 explanation=f"AI inference failed ({type(e).__name__}). Human review required.")
                else:
                    r = AIResult(**base, status="completed", model_name=out["model_name"], model_version=out["model_version"],
                                 predicted_label=out["predicted_label"], predicted_index=out["predicted_index"],
                                 probabilities=out["probabilities"], confidence=out["confidence"],
                                 normalized_entropy=out["normalized_entropy"], is_uncertain=out["is_uncertain"],
                                 display_verdict=out["display_verdict"], explanation=out["explanation"],
                                 inference_ms=out["inference_ms"])
                    db.add(r)
                    db.flush()
                    key = f"hospitals/{s.hospital_id}/screenings/{s.id}/ai/{r.id}_overlay.png"
                    store.put(key, _png(out["overlay_rgb"]))
                    store.put(key.replace("overlay", "heatmap"), _png(out["heatmap_rgb"]))
                    r.gradcam_key = key
        if r not in db:
            db.add(r)
        results.append(r)
    db.flush()
    return results
