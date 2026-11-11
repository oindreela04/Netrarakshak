from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import CurrentUser, client_ip, get_owned, require, tenant_id
from ..models import ConsentRecord, Hospital, Patient, Report, Screening
from ..serializers import consent_out, patient_detail, patient_summary
from ..storage import get_storage

router = APIRouter(prefix="/patients", tags=["patients"])

CONSENT_TYPES = {"screening", "ai_analysis", "data_storage", "research"}


class PatientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)
    date_of_birth: date
    sex: str = Field(default="unspecified", pattern="^(female|male|other|unspecified)$")
    phone: str = Field(default="", max_length=40)
    email: EmailStr | None = None
    address: str = Field(default="", max_length=2000)
    emergency_contact: str = Field(default="", max_length=200)
    abha_id: str = Field(default="", max_length=40)
    medical_history: str = Field(default="", max_length=8000)
    has_diabetes: bool = False
    diabetes_type: str = Field(default="", max_length=20)
    diabetes_since_year: int | None = Field(default=None, ge=1900, le=2100)
    last_hba1c: float | None = Field(default=None, ge=3, le=20)
    has_hypertension: bool = False
    hypertension_since_year: int | None = Field(default=None, ge=1900, le=2100)
    medications: str = Field(default="", max_length=4000)
    branch_id: str | None = None

    @field_validator("date_of_birth")
    @classmethod
    def dob_past(cls, v):
        if v > date.today() or v.year < 1900:
            raise ValueError("Date of birth must be a past date")
        return v


class ConsentIn(BaseModel):
    consent_type: str
    granted: bool
    method: str = Field(default="written", pattern="^(written|digital|verbal_witnessed)$")
    language: str = Field(default="English", max_length=30)
    notes: str = Field(default="", max_length=2000)

    @field_validator("consent_type")
    @classmethod
    def ct(cls, v):
        if v not in CONSENT_TYPES:
            raise ValueError(f"consent_type must be one of {sorted(CONSENT_TYPES)}")
        return v


class PatientCreate(PatientBase):
    is_synthetic: bool = False
    consents: list[ConsentIn] = []


def _next_code(db: Session, h: Hospital) -> str:
    n = db.execute(select(func.count()).select_from(Patient).where(Patient.hospital_id == h.id)).scalar_one()
    while True:
        n += 1
        code = f"NR-{h.code}-{n:06d}"
        if not db.execute(select(Patient.id).where(Patient.hospital_id == h.id, Patient.patient_code == code)).first():
            return code


@router.get("")
def list_patients(q: str = "", diabetes: bool | None = None, hypertension: bool | None = None,
                  archived: bool = False, sex: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(25, le=200),
                  cu: CurrentUser = Depends(require("patients.read")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    stmt = select(Patient).where(Patient.hospital_id == hid, Patient.is_archived.is_(archived))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Patient.first_name.ilike(like), Patient.last_name.ilike(like),
                              Patient.patient_code.ilike(like), Patient.phone.ilike(like),
                              (Patient.first_name + " " + Patient.last_name).ilike(like)))
    if diabetes is not None:
        stmt = stmt.where(Patient.has_diabetes.is_(diabetes))
    if hypertension is not None:
        stmt = stmt.where(Patient.has_hypertension.is_(hypertension))
    if sex:
        stmt = stmt.where(Patient.sex == sex)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Patient.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    return {"total": total, "page": page, "page_size": page_size, "items": [patient_summary(p) for p in rows]}


@router.post("", status_code=201)
def create_patient(body: PatientCreate, request: Request, cu: CurrentUser = Depends(require("patients.write")),
                   db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    h = db.get(Hospital, hid)
    data = body.model_dump(exclude={"consents"})
    data["email"] = data["email"] or ""
    p = Patient(hospital_id=hid, patient_code=_next_code(db, h), created_by=cu.id, **data)
    if p.branch_id is None:
        p.branch_id = cu.user.branch_id
    db.add(p)
    db.flush()
    for c in body.consents:
        db.add(ConsentRecord(patient_id=p.id, hospital_id=hid, recorded_by=cu.id, **c.model_dump()))
    audit.record(db, "patient.created", user=cu, ip=client_ip(request), entity_type="patient", entity_id=p.id,
                 details={"patient_code": p.patient_code, "consents": [c.consent_type for c in body.consents if c.granted]})
    db.refresh(p)
    return patient_detail(p)


@router.get("/{patient_id}")
def get_patient(patient_id: str, request: Request, cu: CurrentUser = Depends(require("patients.read")), db: Session = Depends(get_db)):
    p = get_owned(db, Patient, patient_id, tenant_id(cu))
    audit.record(db, "patient.viewed", user=cu, ip=client_ip(request), entity_type="patient", entity_id=p.id)
    d = patient_detail(p)
    d["reports"] = [{"id": r.id, "report_number": r.report_number, "screening_id": r.screening_id,
                     "review_status": r.review_status, "generated_at": r.generated_at.isoformat()}
                    for r in db.execute(select(Report).where(Report.patient_id == p.id).order_by(Report.generated_at.desc())).scalars()]
    return d


@router.put("/{patient_id}")
def update_patient(patient_id: str, body: PatientBase, request: Request, cu: CurrentUser = Depends(require("patients.write")),
                   db: Session = Depends(get_db)):
    p = get_owned(db, Patient, patient_id, tenant_id(cu))
    if p.is_archived:
        raise HTTPException(409, "Archived patients cannot be edited. Restore the record first.")
    changes = {}
    for k, v in body.model_dump().items():
        if k == "email":
            v = v or ""
        if getattr(p, k) != v:
            changes[k] = True  # record field names only, not values (minimise PHI in logs)
            setattr(p, k, v)
    audit.record(db, "patient.updated", user=cu, ip=client_ip(request), entity_type="patient", entity_id=p.id,
                 details={"fields": sorted(changes)})
    db.refresh(p)
    return patient_detail(p)


@router.post("/{patient_id}/archive")
def archive(patient_id: str, request: Request, cu: CurrentUser = Depends(require("patients.archive")), db: Session = Depends(get_db)):
    p = get_owned(db, Patient, patient_id, tenant_id(cu))
    p.is_archived, p.archived_at = True, datetime.now(timezone.utc)
    audit.record(db, "patient.archived", user=cu, ip=client_ip(request), entity_type="patient", entity_id=p.id)
    return patient_summary(p)


@router.post("/{patient_id}/restore")
def restore(patient_id: str, request: Request, cu: CurrentUser = Depends(require("patients.archive")), db: Session = Depends(get_db)):
    p = get_owned(db, Patient, patient_id, tenant_id(cu))
    p.is_archived, p.archived_at = False, None
    audit.record(db, "patient.restored", user=cu, ip=client_ip(request), entity_type="patient", entity_id=p.id)
    return patient_summary(p)


@router.post("/{patient_id}/consents", status_code=201)
def add_consent(patient_id: str, body: ConsentIn, request: Request, cu: CurrentUser = Depends(require("consent.write")),
                db: Session = Depends(get_db)):
    p = get_owned(db, Patient, patient_id, tenant_id(cu))
    c = ConsentRecord(patient_id=p.id, hospital_id=p.hospital_id, recorded_by=cu.id, **body.model_dump())
    db.add(c)
    db.flush()
    audit.record(db, "consent.recorded", user=cu, ip=client_ip(request), entity_type="patient", entity_id=p.id,
                 details={"type": body.consent_type, "granted": body.granted, "method": body.method})
    return consent_out(c)


@router.post("/{patient_id}/consents/{consent_id}/withdraw")
def withdraw_consent(patient_id: str, consent_id: str, request: Request, cu: CurrentUser = Depends(require("consent.write")),
                     db: Session = Depends(get_db)):
    p = get_owned(db, Patient, patient_id, tenant_id(cu))
    c = db.get(ConsentRecord, consent_id)
    if not c or c.patient_id != p.id:
        raise HTTPException(404, "Consent not found")
    c.withdrawn_at = datetime.now(timezone.utc)
    audit.record(db, "consent.withdrawn", user=cu, ip=client_ip(request), entity_type="patient", entity_id=p.id,
                 details={"type": c.consent_type})
    return consent_out(c)


@router.delete("/{patient_id}")
def erase_patient(patient_id: str, request: Request, confirm_code: str = Query(...),
                  cu: CurrentUser = Depends(require("patients.archive", "hospital.manage")), db: Session = Depends(get_db)):
    """Permanent erasure (e.g. DPDP Act data-principal request, or end of retention). Requires prior archiving and
    the patient code typed as confirmation. Encrypted image blobs are overwritten and removed."""
    p = get_owned(db, Patient, patient_id, tenant_id(cu))
    if not p.is_archived:
        raise HTTPException(409, "Archive the patient before permanent erasure")
    if confirm_code != p.patient_code:
        raise HTTPException(400, "Confirmation code does not match the patient ID")
    store = get_storage()
    code = p.patient_code
    from ..models import AIResult, ClinicalReview, RetinalImage
    screenings = db.execute(select(Screening).where(Screening.patient_id == p.id)).scalars().all()
    for s in screenings:
        for r in s.reports:
            store.delete(r.storage_key); db.delete(r)
        for a in s.ai_results:
            if a.gradcam_key:
                store.delete(a.gradcam_key); store.delete(a.gradcam_key.replace("overlay", "heatmap"))
            db.delete(a)
        db.flush()
        for rv in s.reviews:
            db.delete(rv)
        for i in s.images:
            store.delete(i.storage_key); db.delete(i)
        db.flush()
        db.delete(s)
    db.flush()
    db.delete(p)
    audit.record(db, "patient.erased", user=cu, ip=client_ip(request), entity_type="patient", entity_id=patient_id,
                 details={"patient_code": code, "screenings_erased": len(screenings)})
    return {"ok": True, "erased": code}
