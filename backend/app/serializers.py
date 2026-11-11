"""Explicit output shaping — only whitelisted fields leave the API (no accidental PHI or hash leakage)."""
from datetime import timezone

from .models import AIResult, ClinicalReview, ConsentRecord, Hospital, Patient, Report, RetinalImage, Screening, User


def iso(dt):
    """Always emit timezone-aware UTC ISO strings (SQLite returns naive datetimes)."""
    if not dt:
        return None
    if getattr(dt, "tzinfo", None) is None and hasattr(dt, "hour"):
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "hospital_id": u.hospital_id,
            "branch_id": u.branch_id, "phone": u.phone, "medical_registration_no": u.medical_registration_no,
            "is_active": u.is_active, "must_change_password": u.must_change_password,
            "last_login_at": iso(u.last_login_at), "created_at": iso(u.created_at)}


def hospital_out(h: Hospital, full: bool = True) -> dict:
    d = {"id": h.id, "name": h.name, "slug": h.slug, "code": h.code, "city": h.city, "state": h.state,
         "brand_color": h.brand_color, "has_logo": bool(h.logo_key), "plan_code": h.plan_code,
         "licence_status": h.licence_status, "licence_expires_at": iso(h.licence_expires_at), "is_active": h.is_active}
    if full:
        d.update(email=h.email, phone=h.phone, address=h.address, gstin=h.gstin, report_header=h.report_header,
                 report_footer=h.report_footer, billing_cycle=h.billing_cycle, retention_days=h.retention_days,
                 licence_key=h.licence_key, created_at=iso(h.created_at),
                 branches=[{"id": b.id, "name": b.name, "city": b.city, "address": b.address, "is_active": b.is_active}
                           for b in h.branches])
    return d


def consent_out(c: ConsentRecord) -> dict:
    return {"id": c.id, "consent_type": c.consent_type, "granted": c.granted, "method": c.method, "language": c.language,
            "notes": c.notes, "recorded_by": c.recorded_by, "recorded_at": iso(c.recorded_at), "withdrawn_at": iso(c.withdrawn_at)}


def active_consents(p: Patient) -> dict:
    """Latest decision per consent type (withdrawn counts as not granted)."""
    state: dict[str, bool] = {}
    for c in p.consents:
        state[c.consent_type] = c.granted and c.withdrawn_at is None
    return state


def patient_summary(p: Patient) -> dict:
    last = p.screenings[0] if p.screenings else None
    return {"id": p.id, "patient_code": p.patient_code, "full_name": p.full_name, "first_name": p.first_name,
            "last_name": p.last_name, "date_of_birth": p.date_of_birth.isoformat(), "age": p.age, "sex": p.sex,
            "phone": p.phone, "has_diabetes": p.has_diabetes, "has_hypertension": p.has_hypertension,
            "is_synthetic": p.is_synthetic, "is_archived": p.is_archived, "created_at": iso(p.created_at),
            "screening_count": len(p.screenings), "last_screening_at": iso(last.created_at) if last else None,
            "last_screening_status": last.status if last else None}


def patient_detail(p: Patient) -> dict:
    d = patient_summary(p)
    d.update(email=p.email, address=p.address, emergency_contact=p.emergency_contact, abha_id=p.abha_id,
             medical_history=p.medical_history, diabetes_type=p.diabetes_type, diabetes_since_year=p.diabetes_since_year,
             last_hba1c=p.last_hba1c, hypertension_since_year=p.hypertension_since_year, medications=p.medications,
             branch_id=p.branch_id, updated_at=iso(p.updated_at), archived_at=iso(p.archived_at),
             consents=[consent_out(c) for c in p.consents], consent_state=active_consents(p),
             screenings=[screening_summary(s) for s in p.screenings])
    return d


def image_out(i: RetinalImage) -> dict:
    return {"id": i.id, "eye": i.eye, "original_filename": i.original_filename, "content_type": i.content_type,
            "file_size": i.file_size, "width": i.width, "height": i.height, "sha256": i.sha256,
            "metadata": i.image_metadata, "quality": i.quality, "quality_verdict": i.quality_verdict,
            "is_current": i.is_current, "uploaded_at": iso(i.uploaded_at), "uploaded_by": i.uploaded_by}


def ai_out(r: AIResult) -> dict:
    return {"id": r.id, "image_id": r.image_id, "eye": r.eye, "module": r.module, "status": r.status,
            "model_name": r.model_name, "model_version": r.model_version, "predicted_label": r.predicted_label,
            "predicted_index": r.predicted_index, "probabilities": r.probabilities, "confidence": r.confidence,
            "normalized_entropy": r.normalized_entropy, "is_uncertain": r.is_uncertain,
            "display_verdict": r.display_verdict, "explanation": r.explanation, "has_gradcam": bool(r.gradcam_key),
            "inference_ms": r.inference_ms, "created_at": iso(r.created_at)}


def review_out(r: ClinicalReview) -> dict:
    return {"id": r.id, "reviewer_id": r.reviewer_id, "reviewer_name": r.reviewer.full_name if r.reviewer else "",
            "reviewer_registration_no": r.reviewer.medical_registration_no if r.reviewer else "",
            "eye_findings": r.eye_findings, "overall_impression": r.overall_impression,
            "recommendations": r.recommendations, "referral_recommended": r.referral_recommended,
            "referral_urgency": r.referral_urgency, "referral_to": r.referral_to, "follow_up_months": r.follow_up_months,
            "recapture_requested": r.recapture_requested, "recapture_reason": r.recapture_reason, "status": r.status,
            "signed_at": iso(r.signed_at), "signature_hash": r.signature_hash,
            "created_at": iso(r.created_at), "updated_at": iso(r.updated_at)}


def report_out(r: Report) -> dict:
    return {"id": r.id, "report_number": r.report_number, "screening_id": r.screening_id, "patient_id": r.patient_id,
            "review_status": r.review_status, "sha256": r.sha256, "generated_at": iso(r.generated_at),
            "generated_by": r.generated_by}


def latest_ai(s: Screening) -> list[AIResult]:
    """Most recent AI result per eye for the current images."""
    current = {i.id for i in s.images if i.is_current}
    by_eye: dict[str, AIResult] = {}
    for r in s.ai_results:
        if r.image_id in current:
            by_eye[r.eye] = r
    return [by_eye[e] for e in ("right", "left") if e in by_eye]


def screening_summary(s: Screening) -> dict:
    ai = latest_ai(s)
    signed = next((r for r in reversed(s.reviews) if r.status == "signed"), None)
    return {"id": s.id, "screening_code": s.screening_code, "patient_id": s.patient_id, "status": s.status,
            "created_at": iso(s.created_at), "updated_at": iso(s.updated_at),
            "eyes_uploaded": [e for e in ("right", "left") if any(i.eye == e and i.is_current for i in s.images)],
            "ai_verdicts": {r.eye: r.display_verdict for r in ai},
            "final_grades": {e: v.get("final_grade") for e, v in (signed.eye_findings or {}).items()} if signed else {},
            "report_count": len(s.reports)}


def screening_detail(s: Screening) -> dict:
    d = screening_summary(s)
    d.update(camera_device=s.camera_device, dilated=s.dilated, notes=s.notes, created_by=s.created_by,
             patient=patient_summary(s.patient),
             images=[image_out(i) for i in s.images if i.is_current],
             replaced_images=[image_out(i) for i in s.images if not i.is_current],
             ai_results=[ai_out(r) for r in latest_ai(s)],
             ai_history=[ai_out(r) for r in s.ai_results],
             reviews=[review_out(r) for r in s.reviews],
             reports=[report_out(r) for r in s.reports])
    return d
