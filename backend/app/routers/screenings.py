import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from PIL import ExifTags, Image
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..config import get_settings
from ..database import get_db
from ..deps import CurrentUser, check_licence, client_ip, get_owned, require, tenant_id
from ..models import AIResult, Hospital, Patient, Plan, RetinalImage, Screening, ScreeningStatus
from ..serializers import active_consents, ai_out, image_out, screening_detail, screening_summary
from ..services.analysis import run_screening_analysis
from ..services.quality import assess_quality
from ..storage import get_storage

router = APIRouter(prefix="/screenings", tags=["screenings"])
settings = get_settings()

ALLOWED = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".tif": "image/tiff", ".tiff": "image/tiff"}
MAGIC = [(b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n\x1a\n", "image/png"), (b"II*\x00", "image/tiff"), (b"MM\x00*", "image/tiff")]


class ScreeningCreate(BaseModel):
    patient_id: str
    camera_device: str = Field(default="", max_length=200)
    dilated: bool | None = None
    notes: str = Field(default="", max_length=4000)


def month_usage(db: Session, hospital_id: str) -> int:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.execute(select(func.count()).select_from(Screening)
                      .where(Screening.hospital_id == hospital_id, Screening.created_at >= start)).scalar_one()


@router.post("", status_code=201)
def create_screening(body: ScreeningCreate, request: Request, cu: CurrentUser = Depends(require("screenings.write")),
                     db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    h = check_licence(db, hid)
    p = get_owned(db, Patient, body.patient_id, hid)
    if p.is_archived:
        raise HTTPException(409, "Patient record is archived")
    consents = active_consents(p)
    if not consents.get("screening"):
        raise HTTPException(409, "Patient consent for retinal screening has not been recorded. Record consent first.")
    plan = db.get(Plan, h.plan_code)
    if plan and plan.max_screenings_per_month and month_usage(db, hid) >= plan.max_screenings_per_month:
        raise HTTPException(402, f"Monthly screening limit of the {plan.name} plan reached ({plan.max_screenings_per_month}). Upgrade to continue.")
    n = db.execute(select(func.count()).select_from(Screening).where(Screening.hospital_id == hid)).scalar_one() + 1
    s = Screening(hospital_id=hid, branch_id=cu.user.branch_id or p.branch_id, patient_id=p.id, created_by=cu.id,
                  screening_code=f"SC-{h.code}-{datetime.now():%Y%m%d}-{n:05d}", **body.model_dump(exclude={"patient_id"}))
    db.add(s)
    db.flush()
    audit.record(db, "screening.created", user=cu, ip=client_ip(request), entity_type="screening", entity_id=s.id,
                 details={"patient_id": p.id})
    db.refresh(s)
    return screening_detail(s)


@router.get("")
def list_screenings(status: str | None = None, patient_id: str | None = None, q: str = "",
                    page: int = Query(1, ge=1), page_size: int = Query(25, le=200),
                    cu: CurrentUser = Depends(require("screenings.read")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    stmt = select(Screening).join(Patient).where(Screening.hospital_id == hid)
    if status:
        stmt = stmt.where(Screening.status.in_(status.split(",")))
    if patient_id:
        stmt = stmt.where(Screening.patient_id == patient_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Patient.first_name + " " + Patient.last_name).ilike(like) | Patient.patient_code.ilike(like)
                          | Screening.screening_code.ilike(like))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Screening.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    items = []
    for s in rows:
        d = screening_summary(s)
        d["patient_name"] = s.patient.full_name
        d["patient_code"] = s.patient.patient_code
        d["patient_is_synthetic"] = s.patient.is_synthetic
        items.append(d)
    return {"total": total, "items": items}


@router.get("/{screening_id}")
def get_screening(screening_id: str, request: Request, cu: CurrentUser = Depends(require("screenings.read")),
                  db: Session = Depends(get_db)):
    s = get_owned(db, Screening, screening_id, tenant_id(cu))
    audit.record(db, "screening.viewed", user=cu, ip=client_ip(request), entity_type="screening", entity_id=s.id)
    d = screening_detail(s)
    d["patient_consents"] = active_consents(s.patient)
    return d


def _image_metadata(data: bytes, content_type: str) -> dict:
    meta = {"format": content_type}
    try:
        with Image.open(io.BytesIO(data)) as im:
            meta.update(mode=im.mode, pil_format=im.format)
            if im.info.get("dpi"):
                meta["dpi"] = [float(x) for x in im.info["dpi"]]
            exif = im.getexif()
            for tag_id, val in exif.items():
                tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                if tag in ("Make", "Model", "DateTime", "Software", "ImageDescription", "LensModel"):
                    meta[f"exif_{tag}"] = str(val)[:200]
    except Exception:
        meta["metadata_error"] = "unreadable"
    return meta


@router.post("/{screening_id}/images/{eye}", status_code=201)
async def upload_image(screening_id: str, eye: str, request: Request, file: UploadFile = File(...),
                       source: str = Form("manual_upload"),
                       cu: CurrentUser = Depends(require("screenings.write")), db: Session = Depends(get_db)):
    """Upload (or replace) the photograph for one eye. Replaced images are retained (is_current=False) for audit."""
    hid = tenant_id(cu)
    if eye not in ("right", "left"):
        raise HTTPException(422, "eye must be 'right' or 'left'")
    s = get_owned(db, Screening, screening_id, hid)
    if s.status in (ScreeningStatus.SIGNED.value, ScreeningStatus.REPORTED.value):
        raise HTTPException(409, "This screening has been signed; start a new screening for new images")
    name = (file.filename or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED:
        raise HTTPException(415, "Unsupported file type. Use JPEG, JPG, PNG or TIFF.")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB")
    sniffed = next((ct for sig, ct in MAGIC if data.startswith(sig)), None)
    if sniffed is None or sniffed != ALLOWED[ext]:
        raise HTTPException(415, "File content does not match a JPEG, PNG or TIFF image")
    try:
        q = assess_quality(data, settings.min_image_side_px)
    except ValueError as e:
        raise HTTPException(422, str(e))

    for old in [i for i in s.images if i.eye == eye and i.is_current]:
        old.is_current = False
    img = RetinalImage(screening_id=s.id, hospital_id=hid, eye=eye, storage_key="pending", original_filename=file.filename[:255],
                       content_type=sniffed, file_size=len(data), sha256="", width=q["width"], height=q["height"],
                       image_metadata={**_image_metadata(data, sniffed), "source": source[:40]},
                       quality=q, quality_verdict=q["verdict"], uploaded_by=cu.id)
    db.add(img)
    db.flush()
    img.storage_key = f"hospitals/{hid}/screenings/{s.id}/images/{img.id}{ext}"
    img.sha256 = get_storage().put(img.storage_key, data)
    eyes = {i.eye for i in s.images if i.is_current} | {eye}
    s.status = ScreeningStatus.QUALITY_CHECKED.value if eyes == {"right", "left"} else ScreeningStatus.DRAFT.value
    audit.record(db, "image.uploaded", user=cu, ip=client_ip(request), entity_type="screening", entity_id=s.id,
                 details={"eye": eye, "image_id": img.id, "quality": q["verdict"], "sha256": img.sha256, "source": source[:40]})
    return image_out(img)


@router.get("/{screening_id}/images/{image_id}/file")
def image_file(screening_id: str, image_id: str, request: Request, cu: CurrentUser = Depends(require("images.view")),
               db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    s = get_owned(db, Screening, screening_id, hid)
    img = get_owned(db, RetinalImage, image_id, hid)
    if img.screening_id != s.id:
        raise HTTPException(404, "Image not found")
    data = get_storage().get(img.storage_key)
    if img.content_type == "image/tiff":  # browsers do not render TIFF — serve a lossless PNG rendition
        from ..services.quality import decode_image
        import cv2
        ok, buf = cv2.imencode(".png", decode_image(data))
        data, ctype = buf.tobytes(), "image/png"
    else:
        ctype = img.content_type
    audit.record(db, "image.viewed", user=cu, ip=client_ip(request), entity_type="image", entity_id=img.id)
    return Response(data, media_type=ctype, headers={"Cache-Control": "private, no-store"})


@router.get("/{screening_id}/ai/{result_id}/{kind}")
def gradcam_file(screening_id: str, result_id: str, kind: str, cu: CurrentUser = Depends(require("images.view")),
                 db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    get_owned(db, Screening, screening_id, hid)
    r = get_owned(db, AIResult, result_id, hid)
    if r.screening_id != screening_id or not r.gradcam_key or kind not in ("overlay", "heatmap"):
        raise HTTPException(404, "Explainability image not found")
    key = r.gradcam_key if kind == "overlay" else r.gradcam_key.replace("overlay", "heatmap")
    return Response(get_storage().get(key), media_type="image/png", headers={"Cache-Control": "private, no-store"})


@router.post("/{screening_id}/analyse")
def analyse(screening_id: str, request: Request, cu: CurrentUser = Depends(require("ai.run")), db: Session = Depends(get_db)):
    hid = tenant_id(cu)
    check_licence(db, hid)
    s = get_owned(db, Screening, screening_id, hid)
    if s.status in (ScreeningStatus.SIGNED.value, ScreeningStatus.REPORTED.value):
        raise HTTPException(409, "Screening already signed")
    if not any(i.is_current for i in s.images):
        raise HTTPException(409, "Upload at least one retinal photograph first")
    results = run_screening_analysis(db, s)
    s.status = ScreeningStatus.ANALYSED.value
    audit.record(db, "ai.analysis_run", user=cu, ip=client_ip(request), entity_type="screening", entity_id=s.id,
                 details={"results": [{"eye": r.eye, "status": r.status, "model_version": r.model_version,
                                       "verdict": r.display_verdict} for r in results]})
    db.refresh(s)
    return {"results": [ai_out(r) for r in results], "screening": screening_summary(s)}


@router.get("/{screening_id}/hospital-branding")
def branding(screening_id: str, cu: CurrentUser = Depends(require("screenings.read")), db: Session = Depends(get_db)):
    s = get_owned(db, Screening, screening_id, tenant_id(cu))
    h = db.get(Hospital, s.hospital_id)
    return {"name": h.name, "brand_color": h.brand_color}
