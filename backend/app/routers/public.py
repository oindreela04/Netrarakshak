from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import client_ip
from ..models import DemoRequest, Plan

router = APIRouter(prefix="/public", tags=["public"])


class DemoIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    organisation: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(default="", max_length=40)
    role: str = Field(default="", max_length=100)
    message: str = Field(default="", max_length=4000)
    kind: str = Field(default="demo", pattern="^(demo|contact)$")


@router.post("/enquiries", status_code=201)
def create_enquiry(body: DemoIn, request: Request, db: Session = Depends(get_db)):
    d = DemoRequest(**body.model_dump())
    db.add(d)
    db.flush()
    audit.record(db, f"public.{body.kind}_request", ip=client_ip(request), entity_type="demo_request", entity_id=d.id)
    return {"id": d.id, "message": "Thank you. Our team will contact you within one business day."}


@router.get("/plans")
def plans(db: Session = Depends(get_db)):
    rows = db.execute(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.monthly_price_inr)).scalars()
    return [{"code": p.code, "name": p.name, "description": p.description, "monthly_price_inr": p.monthly_price_inr,
             "annual_price_inr": p.annual_price_inr, "max_screenings_per_month": p.max_screenings_per_month,
             "max_users": p.max_users, "max_branches": p.max_branches, "features": p.features} for p in rows]
