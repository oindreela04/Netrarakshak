"""Seed subscription plans, a platform super-admin and two clearly-labelled DEMO hospitals with staff and
SYNTHETIC patients. Safe to run repeatedly (idempotent).

    python scripts/seed.py              # plans + demo tenants
    python scripts/seed.py --no-demo    # plans + super-admin only (production bootstrap)

Demo password comes from SEED_PASSWORD (default shown below — development only; change it).
"""
import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Branch, ConsentRecord, Hospital, Patient, Plan, Role, User  # noqa: E402
from app.security import hash_password  # noqa: E402

PLANS = [
    dict(code="STARTER", name="Starter", description="Small eye clinics and single-doctor practices",
         monthly_price_inr=14999, annual_price_inr=149990, max_screenings_per_month=300, max_users=5, max_branches=1,
         features={"dr_screening": True, "pdf_reports": True, "custom_branding": False, "analytics": "basic",
                   "audit_export": False, "camera_integration": False, "support": "Email, business hours"}),
    dict(code="PROFESSIONAL", name="Professional", description="Medium hospitals and diagnostic centres",
         monthly_price_inr=39999, annual_price_inr=399990, max_screenings_per_month=1500, max_users=25, max_branches=3,
         features={"dr_screening": True, "pdf_reports": True, "custom_branding": True, "analytics": "advanced",
                   "audit_export": True, "camera_integration": True, "support": "Priority, 8×6"}),
    dict(code="ENTERPRISE", name="Enterprise", description="Multi-branch hospital networks",
         monthly_price_inr=0, annual_price_inr=0, max_screenings_per_month=0, max_users=0, max_branches=0,
         features={"dr_screening": True, "pdf_reports": True, "custom_branding": True, "analytics": "advanced",
                   "audit_export": True, "camera_integration": True, "sso": True, "dedicated_hosting": True,
                   "support": "24×7 with SLA", "pricing": "Custom contract"}),
]

PW = os.getenv("SEED_PASSWORD", "Demo@NetraRakshak2026")


def upsert_user(db, email, **kw):
    u = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not u:
        u = User(email=email, password_hash=hash_password(PW), **kw)
        db.add(u)
    return u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-demo", action="store_true")
    a = ap.parse_args()
    from app.config import get_settings
    demo = not a.no_demo and os.getenv("SEED_DEMO", "true").lower() == "true"
    if demo and get_settings().environment == "production" and not os.getenv("SEED_PASSWORD"):
        sys.exit("Refusing to create demo accounts in production without a private SEED_PASSWORD")
    a.no_demo = not demo
    init_db()
    db = SessionLocal()
    for p in PLANS:
        obj = db.get(Plan, p["code"])
        if not obj:
            db.add(Plan(**p))
    db.flush()
    upsert_user(db, "superadmin@netrarakshak.in", full_name="Platform Administrator", role=Role.SUPER_ADMIN.value)

    if not a.no_demo:
        tenants = [
            ("Aarogya Eye Hospital (DEMO)", "AEH", "Kolkata", "West Bengal", "PROFESSIONAL", "#0B1F3A", "aarogya"),
            ("Sunrise Vision Clinic (DEMO)", "SVC", "Pune", "Maharashtra", "STARTER", "#1F4E79", "sunrise"),
        ]
        for name, code, city, state, plan, color, dom in tenants:
            h = db.execute(select(Hospital).where(Hospital.code == code)).scalar_one_or_none()
            if not h:
                h = Hospital(name=name, code=code, slug=f"{dom}-demo", city=city, state=state, plan_code=plan, brand_color=color,
                             email=f"contact@{dom}.example", phone="+91 00000 00000", address=f"Demo address, {city}",
                             licence_status="active", licence_key=f"NRL-DEMO-{code}",
                             licence_expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                             report_footer="DEMONSTRATION TENANT — synthetic data only.")
                db.add(h)
                db.flush()
                db.add(Branch(hospital_id=h.id, name="Main Campus", city=city))
                db.flush()
            branch = h.branches[0] if h.branches else None
            staff = [("admin", "Hospital Administrator", Role.HOSPITAL_ADMIN.value, ""),
                     ("doctor", "Dr. Ananya Sen (DEMO)", Role.OPHTHALMOLOGIST.value, "WBMC-DEMO-00000"),
                     ("tech", "Rahul Das (DEMO)", Role.TECHNICIAN.value, ""),
                     ("reception", "Priya Banerjee (DEMO)", Role.RECEPTIONIST.value, "")]
            for local, full, role, reg in staff:
                upsert_user(db, f"{local}@{dom}.example", full_name=full, role=role, hospital_id=h.id,
                            branch_id=branch.id if branch else None, medical_registration_no=reg)
            db.flush()
            if not db.execute(select(Patient.id).where(Patient.hospital_id == h.id)).first():
                synth = [("SYNTHETIC", "Patient One", date(1968, 3, 14), "male", True, False),
                         ("SYNTHETIC", "Patient Two", date(1975, 8, 2), "female", True, True),
                         ("SYNTHETIC", "Patient Three", date(1959, 11, 23), "female", False, True)]
                for i, (fn, ln, dob, sex, dm, htn) in enumerate(synth, 1):
                    p = Patient(hospital_id=h.id, branch_id=branch.id if branch else None, patient_code=f"NR-{code}-{i:06d}",
                                first_name=fn, last_name=ln, date_of_birth=dob, sex=sex, has_diabetes=dm,
                                diabetes_type="Type 2" if dm else "", diabetes_since_year=2012 if dm else None,
                                has_hypertension=htn, is_synthetic=True,
                                medical_history="Synthetic record for software demonstration. Not a real person.")
                    db.add(p)
                    db.flush()
                    for ct in ("screening", "ai_analysis", "data_storage"):
                        db.add(ConsentRecord(patient_id=p.id, hospital_id=h.id, consent_type=ct, granted=True, method="digital",
                                             notes="Synthetic demo consent"))
    db.commit()
    print("Seed complete.")
    if not a.no_demo:
        print(f"  Demo password for all demo accounts: {PW}")
        print("  superadmin@netrarakshak.in | admin@aarogya.example | doctor@aarogya.example | tech@aarogya.example | reception@aarogya.example")


if __name__ == "__main__":
    main()
