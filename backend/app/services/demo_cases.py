"""Ready-made SYNTHETIC demo cases for the public demo tenant.

On a fresh demo database (the free host resets its disk on every restart) this creates a handful of clearly
labelled synthetic patients, uploads a right- and left-eye photograph for each, runs the real quality checks and the
real AI models on them, and leaves each screening waiting in the ophthalmologist's review queue. Visitors therefore
see analysed cases immediately, and can still run the full workflow themselves.

Runs in a background thread after the API starts (never delays start-up). Off when ENVIRONMENT=production or
DEMO_CASES_ENABLED=false. Only touches the demo hospital AEH, and only if it has no screenings yet.
"""
import ctypes
import gc
import logging
import threading
import time
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select

from .. import audit
from ..config import get_settings
from ..database import SessionLocal
from ..models import ConsentRecord, Hospital, Patient, RetinalImage, Screening, ScreeningStatus, User
from ..storage import get_storage
from .analysis import run_screening_analysis
from .quality import assess_quality

log = logging.getLogger("netrarakshak.demo")

# (first, last, dob, sex, diabetes, hypertension, history, right eye spec, left eye spec)
# eye spec = (seed, lesions, blur) used by make_synthetic_fundus to pre-generate backend/demo_data/*.jpg (1024 px)
DEMO_DIR = Path(__file__).resolve().parents[2] / "demo_data"
CASES = [
    ("Ramesh", "Iyer", date(1962, 4, 9), "male", True, True, "Type 2 diabetes for 14 years; on metformin and amlodipine.",
     (31, 20, 0.0), (52, 10, 0.0)),
    ("Sunita", "Ghosh", date(1979, 1, 22), "female", True, False, "Type 2 diabetes for 6 years; HbA1c 7.4%.",
     (11, 0, 0.0), (23, 0, 0.0)),
    ("Imran", "Qureshi", date(1955, 9, 30), "male", True, True, "Type 2 diabetes for 20 years; previous laser not recorded.",
     (27, 4, 0.0), (47, 35, 0.0)),
    ("Meera", "Nair", date(1988, 6, 14), "female", True, False, "Type 1 diabetes since childhood.",
     (37, 0, 0.0), (41, 4, 0.0)),
    ("Arjun", "Mehta", date(1970, 12, 3), "male", True, False, "Type 2 diabetes for 9 years. Restless during capture.",
     (64, 10, 9.0), (65, 0, 0.0)),
    ("Lakshmi", "Reddy", date(1958, 2, 17), "female", True, True, "Type 2 diabetes for 17 years; hypertension.",
     (73, 55, 0.0), (91, 20, 0.0)),
]


def _release_memory():
    """Return freed memory to the OS between cases (the free host has 512 MB)."""
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def create_demo_cases(hospital_code: str = "AEH", tech_email: str = "tech@aarogya.example") -> int:
    db = SessionLocal()
    try:
        h = db.execute(select(Hospital).where(Hospital.code == hospital_code)).scalar_one_or_none()
        if not h or db.execute(select(func.count()).select_from(Screening).where(Screening.hospital_id == h.id)).scalar_one():
            return 0
        tech = db.execute(select(User).where(User.email == tech_email)).scalar_one_or_none()
        branch = h.branches[0] if h.branches else None
        store = get_storage()
        n_pat = db.execute(select(func.count()).select_from(Patient).where(Patient.hospital_id == h.id)).scalar_one()
        made = 0
        for k, (fn, ln, dob, sex, dm, htn, hist, right, left) in enumerate(CASES, 1):
            p = Patient(hospital_id=h.id, branch_id=branch.id if branch else None, patient_code=f"NR-{hospital_code}-{n_pat + k:06d}",
                        first_name=fn, last_name=ln, date_of_birth=dob, sex=sex, has_diabetes=dm,
                        diabetes_type="Type 1" if "Type 1" in hist else "Type 2", has_hypertension=htn, is_synthetic=True,
                        medical_history=f"SYNTHETIC demo record, not a real person. {hist}")
            db.add(p)
            db.flush()
            for ct in ("screening", "ai_analysis", "data_storage"):
                db.add(ConsentRecord(patient_id=p.id, hospital_id=h.id, consent_type=ct, granted=True, method="digital",
                                     notes="Synthetic demo consent"))
            s = Screening(hospital_id=h.id, branch_id=p.branch_id, patient_id=p.id, created_by=tech.id if tech else None,
                          screening_code=f"SC-{hospital_code}-{datetime.now():%Y%m%d}-{k:05d}", camera_device="Topcon TRC-NW400 (demo)",
                          dilated=k % 2 == 0, notes="Synthetic photographs generated for the demonstration.")
            db.add(s)
            db.flush()
            for eye, (seed, lesions, blur) in (("right", right), ("left", left)):
                data = (DEMO_DIR / f"SYNTHETIC_{fn}_{eye}.jpg").read_bytes()
                q = assess_quality(data, get_settings().min_image_side_px)
                img = RetinalImage(screening_id=s.id, hospital_id=h.id, eye=eye, storage_key="pending",
                                   original_filename=f"SYNTHETIC_{fn}_{eye}.jpg", content_type="image/jpeg", file_size=len(data),
                                   sha256="", width=q["width"], height=q["height"], image_metadata={"source": "demo_seed"},
                                   quality=q, quality_verdict=q["verdict"], uploaded_by=tech.id if tech else None)
                db.add(img)
                db.flush()
                img.storage_key = f"hospitals/{h.id}/screenings/{s.id}/images/{img.id}.jpg"
                img.sha256 = store.put(img.storage_key, data)
            db.flush()
            db.refresh(s)
            results = run_screening_analysis(db, s)
            s.status = ScreeningStatus.ANALYSED.value
            audit.record(db, "ai.analysis_run", user=tech, hospital_id=h.id, entity_type="screening", entity_id=s.id,
                         details={"demo_seed": True, "results": [{"eye": r.eye, "module": r.module, "verdict": r.display_verdict}
                                                                 for r in results]})
            db.commit()  # commit per case so visitors see cases appear one by one
            made += 1
            log.info("demo case %s %s ready", fn, ln)
            _release_memory()
            time.sleep(1)  # leave CPU for visitors' requests on the small instance
        return made
    except Exception:  # demo data must never take the API down
        log.exception("demo case seeding failed")
        db.rollback()
        return 0
    finally:
        db.close()


def start_in_background():
    s = get_settings()
    if s.environment == "production" or not s.demo_cases_enabled:
        return
    threading.Thread(target=create_demo_cases, name="demo-cases", daemon=True).start()
