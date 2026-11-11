from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import CurrentUser, require, tenant_id
from ..models import AIResult, ClinicalReview, Patient, Report, RetinalImage, Screening

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/dashboard")
def dashboard(days: int = 90, cu: CurrentUser = Depends(require("screenings.read")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    count = lambda m, *w: db.execute(select(func.count()).select_from(m).where(m.hospital_id == hid, *w)).scalar_one()
    screenings = db.execute(select(Screening).where(Screening.hospital_id == hid, Screening.created_at >= since)).scalars().all()
    status_counts = Counter(s.status for s in screenings)

    # daily volume (last `days`)
    daily = defaultdict(int)
    for s in screenings:
        daily[_aware(s.created_at).date().isoformat()] += 1
    series = []
    for i in range(min(days, 90) - 1, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat()
        series.append({"date": d, "screenings": daily.get(d, 0)})

    # image quality distribution
    q = Counter(v for (v,) in db.execute(select(RetinalImage.quality_verdict).where(
        RetinalImage.hospital_id == hid, RetinalImage.uploaded_at >= since)).all())

    # AI status + grade distribution (completed and certain only) — from real stored results
    ai_rows = db.execute(select(AIResult).where(AIResult.hospital_id == hid, AIResult.created_at >= since)).scalars().all()
    ai_status = Counter(r.status for r in ai_rows)
    ai_grades = Counter(r.predicted_label for r in ai_rows if r.status == "completed" and not r.is_uncertain)
    uncertain = sum(1 for r in ai_rows if r.status == "completed" and r.is_uncertain)

    # clinician grades + agreement with AI (signed reviews only)
    signed = db.execute(select(ClinicalReview).where(ClinicalReview.hospital_id == hid, ClinicalReview.status == "signed",
                                                     ClinicalReview.signed_at >= since)).scalars().all()
    final = Counter()
    decisions = Counter()
    referrals = 0
    for r in signed:
        referrals += int(r.referral_recommended)
        for f in (r.eye_findings or {}).values():
            final[f.get("final_grade", "not_assessed")] += 1
            decisions[f.get("ai_decision", "not_applicable")] += 1

    turnaround = []
    for r in signed:
        s = next((x for x in screenings if x.id == r.screening_id), None)
        if s and r.signed_at:
            turnaround.append((_aware(r.signed_at) - _aware(s.created_at)).total_seconds() / 3600)

    return {
        "period_days": days,
        "totals": {"patients": count(Patient, Patient.is_archived.is_(False)),
                   "diabetic_patients": count(Patient, Patient.is_archived.is_(False), Patient.has_diabetes.is_(True)),
                   "screenings": len(screenings), "reports": count(Report, Report.generated_at >= since),
                   "awaiting_review": status_counts.get("analysed", 0) + status_counts.get("in_review", 0),
                   "recapture_requested": status_counts.get("recapture_requested", 0),
                   "signed": status_counts.get("signed", 0) + status_counts.get("reported", 0),
                   "referrals": referrals,
                   "median_turnaround_hours": round(sorted(turnaround)[len(turnaround) // 2], 1) if turnaround else None},
        "status_counts": dict(status_counts), "daily": series, "image_quality": dict(q),
        "ai_status": dict(ai_status), "ai_grades": dict(ai_grades), "ai_uncertain": uncertain,
        "clinician_grades": dict(final), "ai_decisions": dict(decisions),
    }
