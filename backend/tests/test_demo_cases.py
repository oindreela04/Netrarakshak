"""Demo cases: synthetic patients with both eyes uploaded and analysed, created once per demo hospital."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select


def test_demo_cases_created_once(client):
    from app.database import SessionLocal
    from app.models import AIResult, Branch, Hospital, RetinalImage, Screening
    from app.services.demo_cases import CASES, create_demo_cases

    db = SessionLocal()
    h = Hospital(name="Demo Cases Test (DEMO)", code="DCT", slug="dct-demo", city="Kolkata", state="WB",
                 plan_code="PROFESSIONAL", licence_status="active",
                 licence_expires_at=datetime.now(timezone.utc) + timedelta(days=30))
    db.add(h); db.flush(); db.add(Branch(hospital_id=h.id, name="Main")); db.commit()
    hid = h.id
    db.close()

    assert create_demo_cases("DCT", "nobody@example.invalid") == len(CASES)
    assert create_demo_cases("DCT", "nobody@example.invalid") == 0  # idempotent
    db = SessionLocal()
    try:
        n = lambda m, *w: db.execute(select(func.count()).select_from(m).where(m.hospital_id == hid, *w)).scalar_one()
        assert n(Screening, Screening.status == "analysed") == len(CASES)
        assert n(RetinalImage) == 2 * len(CASES)
        assert n(AIResult) == 2 * len(CASES)  # one DR result per eye (model unavailable in tests → human review)
    finally:
        db.close()
