"""Hospital administration: team, branches, branding/settings, subscription view, audit trail."""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import CurrentUser, client_ip, get_current_user, get_owned, require, tenant_id
from ..models import AuditLog, Branch, Hospital, Invoice, Plan, Role, User, UserSession
from ..routers.screenings import month_usage
from ..security import hash_password, validate_password_strength
from ..serializers import hospital_out, iso, user_out
from ..storage import get_storage

router = APIRouter(prefix="/admin", tags=["hospital admin"])

HOSPITAL_ROLES = {Role.HOSPITAL_ADMIN.value, Role.OPHTHALMOLOGIST.value, Role.TECHNICIAN.value, Role.RECEPTIONIST.value}


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    role: str
    phone: str = Field(default="", max_length=40)
    medical_registration_no: str = Field(default="", max_length=60)
    branch_id: str | None = None
    temporary_password: str | None = None


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    role: str
    phone: str = Field(default="", max_length=40)
    medical_registration_no: str = Field(default="", max_length=60)
    branch_id: str | None = None
    is_active: bool = True


class BranchIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    city: str = Field(default="", max_length=100)
    address: str = Field(default="", max_length=2000)
    is_active: bool = True


class HospitalSettings(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40)
    address: str = Field(default="", max_length=2000)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=100)
    gstin: str = Field(default="", max_length=20)
    brand_color: str = Field(default="#0B1F3A", pattern=r"^#[0-9A-Fa-f]{6}$")
    report_header: str = Field(default="", max_length=300)
    report_footer: str = Field(default="", max_length=500)
    retention_days: int = Field(default=2555, ge=365, le=36500)


def _plan_limits(db: Session, hid: str):
    h = db.get(Hospital, hid)
    return h, db.get(Plan, h.plan_code)


def _check_branch(db, hid, branch_id):
    if branch_id:
        get_owned(db, Branch, branch_id, hid)


# ------------------------------------------------------------------ users
@router.get("/users")
def list_users(cu: CurrentUser = Depends(require("users.manage")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    return [user_out(u) for u in db.execute(select(User).where(User.hospital_id == hid).order_by(User.full_name)).scalars()]


@router.post("/users", status_code=201)
def create_user(body: UserCreate, request: Request, cu: CurrentUser = Depends(require("users.manage")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    if body.role not in HOSPITAL_ROLES:
        raise HTTPException(422, "Invalid role")
    if body.role == Role.OPHTHALMOLOGIST.value and not body.medical_registration_no:
        raise HTTPException(422, "Ophthalmologists require a medical council registration number")
    _check_branch(db, hid, body.branch_id)
    h, plan = _plan_limits(db, hid)
    active = db.execute(select(func.count()).select_from(User).where(User.hospital_id == hid, User.is_active.is_(True))).scalar_one()
    if plan.max_users and active >= plan.max_users:
        raise HTTPException(402, f"The {plan.name} plan allows {plan.max_users} active users. Upgrade to add more.")
    if db.execute(select(User.id).where(User.email == body.email.lower())).first():
        raise HTTPException(409, "A user with this email already exists")
    temp = body.temporary_password or ("Nr-" + secrets.token_urlsafe(9) + "7!")
    try:
        validate_password_strength(temp)
    except ValueError as e:
        raise HTTPException(422, str(e))
    u = User(hospital_id=hid, email=body.email.lower(), full_name=body.full_name, role=body.role, phone=body.phone,
             medical_registration_no=body.medical_registration_no, branch_id=body.branch_id,
             password_hash=hash_password(temp), must_change_password=True)
    db.add(u)
    db.flush()
    audit.record(db, "user.created", user=cu, ip=client_ip(request), entity_type="user", entity_id=u.id, details={"role": u.role})
    return {**user_out(u), "temporary_password": temp}


@router.put("/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, request: Request, cu: CurrentUser = Depends(require("users.manage")),
                db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    u = get_owned(db, User, user_id, hid)
    if body.role not in HOSPITAL_ROLES:
        raise HTTPException(422, "Invalid role")
    if u.id == cu.id and (not body.is_active or body.role != u.role):
        raise HTTPException(409, "You cannot deactivate yourself or change your own role")
    _check_branch(db, hid, body.branch_id)
    for k, v in body.model_dump().items():
        setattr(u, k, v)
    if not u.is_active:
        for s in db.execute(select(UserSession).where(UserSession.user_id == u.id, UserSession.revoked_at.is_(None))).scalars():
            s.revoked_at = datetime.now(timezone.utc)
    audit.record(db, "user.updated", user=cu, ip=client_ip(request), entity_type="user", entity_id=u.id,
                 details={"role": u.role, "active": u.is_active})
    return user_out(u)


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, request: Request, cu: CurrentUser = Depends(require("users.manage")), db: Session = Depends(get_db)):
    u = get_owned(db, User, user_id, tenant_id(cu))
    temp = "Nr-" + secrets.token_urlsafe(9) + "7!"
    u.password_hash, u.must_change_password, u.failed_logins, u.locked_until = hash_password(temp), True, 0, None
    for s in db.execute(select(UserSession).where(UserSession.user_id == u.id, UserSession.revoked_at.is_(None))).scalars():
        s.revoked_at = datetime.now(timezone.utc)
    audit.record(db, "user.password_reset", user=cu, ip=client_ip(request), entity_type="user", entity_id=u.id)
    return {"temporary_password": temp}


# ------------------------------------------------------------------ branches
@router.get("/branches")
def list_branches(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    return [{"id": b.id, "name": b.name, "city": b.city, "address": b.address, "is_active": b.is_active}
            for b in db.execute(select(Branch).where(Branch.hospital_id == hid).order_by(Branch.name)).scalars()]


@router.post("/branches", status_code=201)
def create_branch(body: BranchIn, request: Request, cu: CurrentUser = Depends(require("branches.manage")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    h, plan = _plan_limits(db, hid)
    n = db.execute(select(func.count()).select_from(Branch).where(Branch.hospital_id == hid, Branch.is_active.is_(True))).scalar_one()
    if plan.max_branches and n >= plan.max_branches:
        raise HTTPException(402, f"The {plan.name} plan allows {plan.max_branches} branch(es). Upgrade to Enterprise for multi-branch.")
    b = Branch(hospital_id=hid, **body.model_dump())
    db.add(b)
    db.flush()
    audit.record(db, "branch.created", user=cu, ip=client_ip(request), entity_type="branch", entity_id=b.id)
    return {"id": b.id, "name": b.name, "city": b.city, "address": b.address, "is_active": b.is_active}


@router.put("/branches/{branch_id}")
def update_branch(branch_id: str, body: BranchIn, request: Request, cu: CurrentUser = Depends(require("branches.manage")),
                  db: Session = Depends(get_db)):
    b = get_owned(db, Branch, branch_id, tenant_id(cu))
    for k, v in body.model_dump().items():
        setattr(b, k, v)
    audit.record(db, "branch.updated", user=cu, ip=client_ip(request), entity_type="branch", entity_id=b.id)
    return {"id": b.id, "name": b.name, "city": b.city, "address": b.address, "is_active": b.is_active}


# ------------------------------------------------------------------ hospital settings / branding
@router.get("/hospital")
def get_hospital(cu: CurrentUser = Depends(require("hospital.manage")), db: Session = Depends(get_db)):
    return hospital_out(db.get(Hospital, tenant_id(cu)))


@router.put("/hospital")
def update_hospital(body: HospitalSettings, request: Request, cu: CurrentUser = Depends(require("hospital.manage")),
                    db: Session = Depends(get_db)):
    h = db.get(Hospital, tenant_id(cu))
    for k, v in body.model_dump().items():
        setattr(h, k, v)
    audit.record(db, "hospital.settings_updated", user=cu, ip=client_ip(request), entity_type="hospital", entity_id=h.id)
    return hospital_out(h)


@router.post("/hospital/logo")
async def upload_logo(request: Request, file: UploadFile = File(...), cu: CurrentUser = Depends(require("hospital.manage")),
                      db: Session = Depends(get_db)):
    h = db.get(Hospital, tenant_id(cu))
    data = await file.read()
    if len(data) > 2 * 1024 * 1024 or not (data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8\xff")):
        raise HTTPException(415, "Logo must be a PNG or JPEG under 2 MB")
    ext = "png" if data.startswith(b"\x89PNG") else "jpg"
    key = f"hospitals/{h.id}/branding/logo.{ext}"
    get_storage().put(key, data)
    h.logo_key = key
    audit.record(db, "hospital.logo_updated", user=cu, ip=client_ip(request), entity_type="hospital", entity_id=h.id)
    return {"ok": True}


@router.get("/hospital/logo")
def get_logo(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.get(Hospital, tenant_id(cu))
    if not h.logo_key:
        raise HTTPException(404, "No logo")
    return Response(get_storage().get(h.logo_key), media_type="image/png" if h.logo_key.endswith("png") else "image/jpeg")


# ------------------------------------------------------------------ subscription (read-only for hospitals)
@router.get("/subscription")
def subscription(cu: CurrentUser = Depends(require("subscription.read")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    h, plan = _plan_limits(db, hid)
    users = db.execute(select(func.count()).select_from(User).where(User.hospital_id == hid, User.is_active.is_(True))).scalar_one()
    branches = db.execute(select(func.count()).select_from(Branch).where(Branch.hospital_id == hid, Branch.is_active.is_(True))).scalar_one()
    invoices = db.execute(select(Invoice).where(Invoice.hospital_id == hid).order_by(Invoice.issued_at.desc())).scalars()
    return {
        "plan": {"code": plan.code, "name": plan.name, "description": plan.description, "monthly_price_inr": plan.monthly_price_inr,
                 "annual_price_inr": plan.annual_price_inr, "features": plan.features},
        "billing_cycle": h.billing_cycle, "licence_status": h.licence_status, "licence_key": h.licence_key,
        "licence_expires_at": iso(h.licence_expires_at),
        "usage": {"screenings_this_month": month_usage(db, hid), "screenings_limit": plan.max_screenings_per_month,
                  "active_users": users, "users_limit": plan.max_users, "branches": branches, "branches_limit": plan.max_branches},
        "invoices": [{"id": i.id, "invoice_number": i.invoice_number, "period_start": i.period_start.isoformat(),
                      "period_end": i.period_end.isoformat(), "total_inr": i.total_inr, "gst_inr": i.gst_inr,
                      "subtotal_inr": i.subtotal_inr, "status": i.status, "issued_at": iso(i.issued_at),
                      "line_items": i.line_items} for i in invoices],
    }


# ------------------------------------------------------------------ audit
@router.get("/audit")
def audit_logs(action: str = "", user_id: str = "", page: int = Query(1, ge=1), page_size: int = Query(50, le=500),
               cu: CurrentUser = Depends(require("audit.read")), db: Session = Depends(get_db)):
    stmt = select(AuditLog)
    if cu.hospital_id:
        stmt = stmt.where(AuditLog.hospital_id == cu.hospital_id)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    return {"total": total, "items": [{"id": a.id, "action": a.action, "user_email": a.user_email, "entity_type": a.entity_type,
                                       "entity_id": a.entity_id, "ip_address": a.ip_address,
                                       "details": {k: v for k, v in (a.details or {}).items() if k != "_ts"},
                                       "created_at": iso(a.created_at), "hash": a.hash[:16]} for a in rows]}
