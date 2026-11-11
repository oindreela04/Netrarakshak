"""Hash-chained, append-only audit trail. Each entry stores SHA-256(prev_hash + canonical entry)."""
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditLog, utcnow


def _digest(prev: str, entry: dict) -> str:
    return hashlib.sha256((prev + json.dumps(entry, sort_keys=True, default=str)).encode()).hexdigest()


def record(db: Session, action: str, *, user=None, hospital_id: str | None = None, entity_type: str = "",
           entity_id: str = "", ip: str = "", details: dict | None = None, commit: bool = True) -> AuditLog:
    u = getattr(user, "user", user)  # accepts CurrentUser or User
    last = db.execute(select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none() or ""
    entry = {
        "hospital_id": hospital_id if hospital_id is not None else getattr(u, "hospital_id", None),
        "user_id": getattr(u, "id", None), "user_email": getattr(u, "email", "") or "",
        "action": action, "entity_type": entity_type, "entity_id": str(entity_id or ""),
        "ip_address": ip, "details": details or {}, "created_at": utcnow().isoformat(),
    }
    log = AuditLog(**{**entry, "created_at": utcnow()}, prev_hash=last, hash=_digest(last, entry))
    log.details = {**(details or {}), "_ts": entry["created_at"]}
    db.add(log)
    if commit:
        db.commit()
    return log


def verify_chain(db: Session) -> dict:
    prev = ""
    count = 0
    for log in db.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        details = dict(log.details or {})
        ts = details.pop("_ts", None)
        entry = {"hospital_id": log.hospital_id, "user_id": log.user_id, "user_email": log.user_email,
                 "action": log.action, "entity_type": log.entity_type, "entity_id": log.entity_id,
                 "ip_address": log.ip_address, "details": details, "created_at": ts}
        if log.prev_hash != prev or _digest(prev, entry) != log.hash:
            return {"valid": False, "broken_at_id": log.id, "checked": count}
        prev = log.hash
        count += 1
    return {"valid": True, "checked": count}
