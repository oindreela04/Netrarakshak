"""Data-retention report: lists ARCHIVED patients whose last activity is older than their hospital's retention
period. Erasure itself is a deliberate, audited action by a hospital administrator (Patient profile →
Erase permanently, or DELETE /api/patients/{id}). Run monthly, e.g. via Windows Task Scheduler or cron.

    python scripts/retention_report.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import Hospital, Patient  # noqa: E402


def main():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    due = 0
    for h in db.execute(select(Hospital)).scalars():
        cutoff = now - timedelta(days=h.retention_days)
        for p in db.execute(select(Patient).where(Patient.hospital_id == h.id, Patient.is_archived.is_(True))).scalars():
            last = max([p.updated_at] + [s.created_at for s in p.screenings])
            last = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
            if last < cutoff:
                due += 1
                print(f"{h.name} | {p.patient_code} | last activity {last:%Y-%m-%d} | retention {h.retention_days} d")
    print(f"{due} archived record(s) past retention.")


if __name__ == "__main__":
    main()
