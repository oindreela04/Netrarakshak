"""Super-administrator (platform operator) endpoints. No patient-level data is exposed here."""
import re
import secrets
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import CurrentUser, client_ip, require
from ..models import Branch, DemoRequest, Hospital, Invoice, Patient, Plan, Report, Role, Screening, User
from ..routers.screenings import month_usage
from ..security import hash_password
from ..serializers import hospital_out, iso
from ..services.billing import get_billing_provider

router = APIRouter(prefix="/platform", tags=["super admin"])
SA = require("platform.manage")


class HospitalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=8, pattern="^[A-Z0-9]+$")
    city: str = ""
    state: str = ""
    email: str = ""
    phone: str = ""
    plan_code: str = "STARTER"
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|annual)$")
    licence_status: str = Field(default="trial", pattern="^(trial|active|suspended|expired)$")
    licence_expires_at: datetime | None = None
    admin_email: EmailStr
    admin_name: str = Field(min_length=2)


class HospitalAdminUpdate(BaseModel):
    plan_code: str
    billing_cycle: str = Field(pattern="^(monthly|annual)$")
    licence_status: str = Field(pattern="^(trial|active|suspended|expired)$")
    licence_expires_at: datetime | None = None
    is_active: bool = True


class PlanUpdate(BaseModel):
    name: str
    description: str = ""
    monthly_price_inr: int = Field(ge=0)
    annual_price_inr: int = Field(ge=0)
    max_screenings_per_month: int = Field(ge=0)
    max_users: int = Field(ge=0)
    max_branches: int = Field(ge=0)
    features: dict = {}
    is_active: bool = True


class PaidIn(BaseModel):
    reference: str = Field(min_length=2, max_length=100)


@router.get("/stats")
def stats(cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    c = lambda m, *w: db.execute(select(func.count()).select_from(m).where(*w)).scalar_one()
    mrr = 0
    for h in db.execute(select(Hospital).where(Hospital.licence_status == "active")).scalars():
        p = db.get(Plan, h.plan_code)
        mrr += p.monthly_price_inr if h.billing_cycle == "monthly" else p.annual_price_inr // 12
    return {"hospitals": c(Hospital), "active_licences": c(Hospital, Hospital.licence_status == "active"),
            "trials": c(Hospital, Hospital.licence_status == "trial"), "users": c(User),
            "patients": c(Patient), "screenings": c(Screening), "reports": c(Report),
            "open_enquiries": c(DemoRequest, DemoRequest.status == "new"), "mrr_inr": mrr}


@router.get("/hospitals")
def hospitals(cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    out = []
    for h in db.execute(select(Hospital).order_by(Hospital.created_at)).scalars():
        d = hospital_out(h)
        d["usage"] = {"screenings_this_month": month_usage(db, h.id),
                      "users": db.execute(select(func.count()).select_from(User).where(User.hospital_id == h.id)).scalar_one(),
                      "branches": db.execute(select(func.count()).select_from(Branch).where(Branch.hospital_id == h.id)).scalar_one()}
        out.append(d)
    return out


@router.post("/hospitals", status_code=201)
def create_hospital(body: HospitalCreate, request: Request, cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    if db.execute(select(Hospital.id).where(Hospital.code == body.code)).first():
        raise HTTPException(409, "Hospital code already in use")
    if db.execute(select(User.id).where(User.email == body.admin_email.lower())).first():
        raise HTTPException(409, "Admin email already in use")
    if not db.get(Plan, body.plan_code):
        raise HTTPException(422, "Unknown plan")
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")[:60] + "-" + body.code.lower()
    h = Hospital(name=body.name, code=body.code, slug=slug, city=body.city, state=body.state, email=body.email, phone=body.phone,
                 plan_code=body.plan_code, billing_cycle=body.billing_cycle, licence_status=body.licence_status,
                 licence_expires_at=body.licence_expires_at, licence_key="NRL-" + secrets.token_hex(10).upper())
    db.add(h)
    db.flush()
    db.add(Branch(hospital_id=h.id, name="Main", city=body.city))
    temp = "Nr-" + secrets.token_urlsafe(9) + "7!"
    db.add(User(hospital_id=h.id, email=body.admin_email.lower(), full_name=body.admin_name, role=Role.HOSPITAL_ADMIN.value,
                password_hash=hash_password(temp), must_change_password=True))
    audit.record(db, "platform.hospital_created", user=cu, hospital_id=h.id, ip=client_ip(request), entity_type="hospital", entity_id=h.id)
    db.refresh(h)
    return {**hospital_out(h), "admin_temporary_password": temp}


@router.put("/hospitals/{hospital_id}")
def update_hospital(hospital_id: str, body: HospitalAdminUpdate, request: Request, cu: CurrentUser = Depends(SA),
                    db: Session = Depends(get_db)):
    h = db.get(Hospital, hospital_id)
    if not h:
        raise HTTPException(404, "Hospital not found")
    if not db.get(Plan, body.plan_code):
        raise HTTPException(422, "Unknown plan")
    before = {"plan": h.plan_code, "licence": h.licence_status, "active": h.is_active}
    for k, v in body.model_dump().items():
        setattr(h, k, v)
    audit.record(db, "platform.hospital_updated", user=cu, hospital_id=h.id, ip=client_ip(request), entity_type="hospital",
                 entity_id=h.id, details={"before": before, "after": {"plan": h.plan_code, "licence": h.licence_status, "active": h.is_active}})
    return hospital_out(h)


@router.get("/plans")
def plans(cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    return [{"code": p.code, "name": p.name, "description": p.description, "monthly_price_inr": p.monthly_price_inr,
             "annual_price_inr": p.annual_price_inr, "max_screenings_per_month": p.max_screenings_per_month,
             "max_users": p.max_users, "max_branches": p.max_branches, "features": p.features, "is_active": p.is_active}
            for p in db.execute(select(Plan).order_by(Plan.monthly_price_inr)).scalars()]


@router.put("/plans/{code}")
def update_plan(code: str, body: PlanUpdate, request: Request, cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    p = db.get(Plan, code)
    if not p:
        raise HTTPException(404, "Plan not found")
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    audit.record(db, "platform.plan_updated", user=cu, ip=client_ip(request), entity_type="plan", entity_id=code)
    return {"ok": True}


@router.get("/invoices")
def invoices(cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    rows = db.execute(select(Invoice, Hospital).join(Hospital).order_by(Invoice.issued_at.desc())).all()
    return [{"id": i.id, "invoice_number": i.invoice_number, "hospital": h.name, "hospital_id": h.id, "plan_code": i.plan_code,
             "period_start": i.period_start.isoformat(), "period_end": i.period_end.isoformat(), "total_inr": i.total_inr,
             "status": i.status, "issued_at": iso(i.issued_at), "paid_at": iso(i.paid_at), "payment_reference": i.payment_reference}
            for i, h in rows]


@router.post("/hospitals/{hospital_id}/invoices", status_code=201)
def issue_invoice(hospital_id: str, request: Request, cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    h = db.get(Hospital, hospital_id)
    if not h:
        raise HTTPException(404, "Hospital not found")
    inv = get_billing_provider().create_invoice(db, h, db.get(Plan, h.plan_code), date.today())
    db.flush()
    audit.record(db, "billing.invoice_issued", user=cu, hospital_id=h.id, ip=client_ip(request), entity_type="invoice", entity_id=inv.id)
    return {"id": inv.id, "invoice_number": inv.invoice_number, "total_inr": inv.total_inr}


@router.post("/invoices/{invoice_id}/paid")
def mark_paid(invoice_id: str, body: PaidIn, request: Request, cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    get_billing_provider().mark_paid(inv, body.reference)
    h = db.get(Hospital, inv.hospital_id)
    if h.licence_status in ("trial", "expired"):
        h.licence_status = "active"
    if not h.licence_expires_at or (h.licence_expires_at.replace(tzinfo=timezone.utc) if not h.licence_expires_at.tzinfo else h.licence_expires_at).date() < inv.period_end:
        h.licence_expires_at = datetime.combine(inv.period_end, datetime.max.time()).replace(tzinfo=timezone.utc)
    audit.record(db, "billing.invoice_paid", user=cu, hospital_id=h.id, ip=client_ip(request), entity_type="invoice", entity_id=inv.id)
    return {"ok": True}


@router.get("/enquiries")
def enquiries(cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    return [{"id": d.id, "name": d.name, "organisation": d.organisation, "email": d.email, "phone": d.phone, "role": d.role,
             "kind": d.kind, "message": d.message, "status": d.status, "created_at": iso(d.created_at)}
            for d in db.execute(select(DemoRequest).order_by(DemoRequest.created_at.desc())).scalars()]


@router.post("/enquiries/{eid}/status/{status}")
def enquiry_status(eid: str, status: str, cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    d = db.get(DemoRequest, eid)
    if not d or status not in ("new", "contacted", "closed"):
        raise HTTPException(404, "Not found")
    d.status = status
    db.commit()
    return {"ok": True}


@router.get("/audit/verify")
def verify(cu: CurrentUser = Depends(SA), db: Session = Depends(get_db)):
    return audit.verify_chain(db)
