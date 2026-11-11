import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import CurrentUser, client_ip, get_owned, require, tenant_id
from ..models import ClinicalReview, Screening, ScreeningStatus
from ..security import verify_password
from ..serializers import latest_ai, review_out, screening_summary

router = APIRouter(prefix="/reviews", tags=["clinical review"])

GRADES = {"no_dr", "mild_npdr", "moderate_npdr", "severe_npdr", "proliferative_dr", "ungradable", "not_assessed"}
DECISIONS = {"accept", "modify", "reject", "not_applicable"}


class EyeFinding(BaseModel):
    ai_decision: str = "not_applicable"
    final_grade: str = "not_assessed"
    macular_oedema_suspected: bool | None = None
    other_findings: str = Field(default="", max_length=2000)
    observations: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def check(self):
        if self.ai_decision not in DECISIONS:
            raise ValueError(f"ai_decision must be one of {sorted(DECISIONS)}")
        if self.final_grade not in GRADES:
            raise ValueError(f"final_grade must be one of {sorted(GRADES)}")
        return self


class ReviewIn(BaseModel):
    eye_findings: dict[str, EyeFinding] = {}
    overall_impression: str = Field(default="", max_length=8000)
    recommendations: str = Field(default="", max_length=8000)
    referral_recommended: bool = False
    referral_urgency: str = Field(default="", pattern="^(|routine|soon|urgent)$")
    referral_to: str = Field(default="", max_length=200)
    follow_up_months: int | None = Field(default=None, ge=0, le=60)


class RecaptureIn(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)
    eyes: list[str] = ["right", "left"]


class SignIn(BaseModel):
    password: str
    attestation: bool


@router.get("/queue")
def queue(cu: CurrentUser = Depends(require("review.write")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    rows = db.execute(select(Screening).where(Screening.hospital_id == hid, Screening.status.in_(
        [ScreeningStatus.ANALYSED.value, ScreeningStatus.IN_REVIEW.value, ScreeningStatus.QUALITY_CHECKED.value]))
        .order_by(Screening.created_at)).scalars()
    out = []
    for s in rows:
        d = screening_summary(s)
        ai = latest_ai(s)
        d.update(patient_name=s.patient.full_name, patient_code=s.patient.patient_code, patient_age=s.patient.age,
                 has_diabetes=s.patient.has_diabetes, patient_is_synthetic=s.patient.is_synthetic,
                 needs_attention=any(r.is_uncertain or r.status != "completed" for r in ai) or not ai,
                 referable_suggested=any(r.status == "completed" and (r.predicted_index or 0) >= 2 for r in ai))
        out.append(d)
    out.sort(key=lambda d: (not d["referable_suggested"], not d["needs_attention"], d["created_at"]))
    return out


def _draft(db: Session, s: Screening, cu: CurrentUser) -> ClinicalReview:
    r = next((r for r in reversed(s.reviews) if r.status == "draft" and r.reviewer_id == cu.id), None)
    if not r:
        r = ClinicalReview(screening_id=s.id, hospital_id=s.hospital_id, reviewer_id=cu.id)
        db.add(r)
    return r


def _validate_against_ai(s: Screening, body: ReviewIn):
    ai = {r.eye: r for r in latest_ai(s)}
    for eye, f in body.eye_findings.items():
        if eye not in ("right", "left"):
            raise HTTPException(422, "eye keys must be 'right' or 'left'")
        r = ai.get(eye)
        if r and r.status == "completed":
            if f.ai_decision == "not_applicable":
                raise HTTPException(422, f"{eye} eye: state whether you accept, modify or reject the AI finding")
            if f.ai_decision == "accept":
                keys = list((r.probabilities or {}).keys())
                if r.predicted_index is not None and keys and f.final_grade != keys[r.predicted_index]:
                    raise HTTPException(422, f"{eye} eye: 'accept' requires the final grade to match the AI suggestion; use 'modify' instead")
        elif f.ai_decision in ("accept", "modify"):
            raise HTTPException(422, f"{eye} eye: there is no completed AI finding to accept or modify")


@router.put("/screening/{screening_id}")
def save_review(screening_id: str, body: ReviewIn, request: Request, cu: CurrentUser = Depends(require("review.write")),
                db: Session = Depends(get_db)):
    s = get_owned(db, Screening, screening_id, tenant_id(cu))
    if s.status in (ScreeningStatus.SIGNED.value, ScreeningStatus.REPORTED.value):
        raise HTTPException(409, "Review already signed")
    _validate_against_ai(s, body)
    r = _draft(db, s, cu)
    r.eye_findings = {k: v.model_dump() for k, v in body.eye_findings.items()}
    for k in ("overall_impression", "recommendations", "referral_recommended", "referral_urgency", "referral_to", "follow_up_months"):
        setattr(r, k, getattr(body, k))
    s.status = ScreeningStatus.IN_REVIEW.value
    db.flush()
    audit.record(db, "review.saved", user=cu, ip=client_ip(request), entity_type="screening", entity_id=s.id,
                 details={"review_id": r.id, "decisions": {e: f.ai_decision for e, f in body.eye_findings.items()}})
    db.refresh(r)
    return review_out(r)


@router.post("/screening/{screening_id}/request-recapture")
def request_recapture(screening_id: str, body: RecaptureIn, request: Request, cu: CurrentUser = Depends(require("review.write")),
                      db: Session = Depends(get_db)):
    s = get_owned(db, Screening, screening_id, tenant_id(cu))
    if s.status in (ScreeningStatus.SIGNED.value, ScreeningStatus.REPORTED.value):
        raise HTTPException(409, "Review already signed")
    r = _draft(db, s, cu)
    r.recapture_requested, r.recapture_reason = True, f"[{', '.join(body.eyes)}] {body.reason}"
    s.status = ScreeningStatus.RECAPTURE_REQUESTED.value
    db.flush()
    audit.record(db, "review.recapture_requested", user=cu, ip=client_ip(request), entity_type="screening", entity_id=s.id,
                 details={"eyes": body.eyes})
    return review_out(r)


@router.post("/screening/{screening_id}/sign")
def sign(screening_id: str, body: SignIn, request: Request, cu: CurrentUser = Depends(require("review.sign")),
         db: Session = Depends(get_db)):
    """Clinician approval. Requires re-entering the password (signature intent) and an explicit attestation."""
    s = get_owned(db, Screening, screening_id, tenant_id(cu))
    r = next((r for r in reversed(s.reviews) if r.status == "draft" and r.reviewer_id == cu.id), None)
    if not r:
        raise HTTPException(409, "Save your review before signing")
    if not body.attestation:
        raise HTTPException(422, "You must attest that you personally reviewed the images and findings")
    if not verify_password(body.password, cu.user.password_hash):
        audit.record(db, "review.sign_failed", user=cu, ip=client_ip(request), entity_type="screening", entity_id=s.id)
        raise HTTPException(401, "Password incorrect — signature not applied")
    if not r.eye_findings or all(f.get("final_grade") == "not_assessed" for f in r.eye_findings.values()):
        raise HTTPException(422, "Record a final grade for at least one eye before signing")
    if not cu.user.medical_registration_no:
        raise HTTPException(422, "Your profile has no medical registration number; ask your administrator to add it")
    now = datetime.now(timezone.utc)
    payload = json.dumps({"review": r.id, "screening": s.id, "reviewer": cu.id, "reg": cu.user.medical_registration_no,
                          "findings": r.eye_findings, "impression": r.overall_impression, "rec": r.recommendations,
                          "referral": [r.referral_recommended, r.referral_urgency, r.referral_to], "at": now.isoformat()},
                         sort_keys=True)
    r.signature_hash = hashlib.sha256(payload.encode()).hexdigest()
    r.status, r.signed_at = "signed", now
    s.status = ScreeningStatus.SIGNED.value
    audit.record(db, "review.signed", user=cu, ip=client_ip(request), entity_type="screening", entity_id=s.id,
                 details={"review_id": r.id, "signature_hash": r.signature_hash})
    db.refresh(r)
    return review_out(r)
