from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import CurrentUser, client_ip, get_owned, require, tenant_id
from ..models import Hospital, Patient, Report, Screening, ScreeningStatus
from ..serializers import report_out
from ..services.report_pdf import build_report
from ..storage import get_storage

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/screening/{screening_id}", status_code=201)
def generate(screening_id: str, request: Request, cu: CurrentUser = Depends(require("reports.generate")),
             db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    s = get_owned(db, Screening, screening_id, hid)
    if not any(i.is_current for i in s.images):
        raise HTTPException(409, "No images in this screening")
    h = db.get(Hospital, hid)
    n = db.execute(select(func.count()).select_from(Report).where(Report.hospital_id == hid)).scalar_one() + 1
    number = f"RPT-{h.code}-{datetime.now():%Y%m%d}-{n:05d}"
    pdf, status = build_report(s, h, number, cu.user.full_name)
    key = f"hospitals/{hid}/reports/{number}.pdf"
    sha = get_storage().put(key, pdf)
    signed = next((r for r in reversed(s.reviews) if r.status == "signed"), None)
    r = Report(report_number=number, screening_id=s.id, hospital_id=hid, patient_id=s.patient_id,
               review_id=signed.id if signed else None, review_status=status, storage_key=key, sha256=sha, generated_by=cu.id)
    db.add(r)
    if signed:
        s.status = ScreeningStatus.REPORTED.value
    db.flush()
    audit.record(db, "report.generated", user=cu, ip=client_ip(request), entity_type="report", entity_id=r.id,
                 details={"report_number": number, "status": status, "sha256": sha})
    return report_out(r)


@router.get("")
def list_reports(q: str = "", page: int = Query(1, ge=1), page_size: int = Query(25, le=200),
                 cu: CurrentUser = Depends(require("reports.read")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    stmt = select(Report, Patient).join(Patient, Patient.id == Report.patient_id).where(Report.hospital_id == hid)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Report.report_number.ilike(like) | Patient.patient_code.ilike(like)
                          | (Patient.first_name + " " + Patient.last_name).ilike(like))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Report.generated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"total": total, "items": [{**report_out(r), "patient_name": p.full_name, "patient_code": p.patient_code,
                                       "patient_is_synthetic": p.is_synthetic} for r, p in rows]}


@router.get("/{report_id}/file")
def download(report_id: str, request: Request, download: bool = False, cu: CurrentUser = Depends(require("reports.read")),
             db: Session = Depends(get_db)):
    r = get_owned(db, Report, report_id, tenant_id(cu))
    pdf = get_storage().get(r.storage_key)
    audit.record(db, "report.downloaded" if download else "report.viewed", user=cu, ip=client_ip(request),
                 entity_type="report", entity_id=r.id)
    disp = "attachment" if download else "inline"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'{disp}; filename="{r.report_number}.pdf"', "Cache-Control": "private, no-store"})
