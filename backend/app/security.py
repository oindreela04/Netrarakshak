"""Password hashing, token issuance, password policy and the role → permission matrix."""
import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings
from .models import Role

settings = get_settings()

# ---------------------------------------------------------------- passwords
PASSWORD_RULES = "At least 10 characters, with upper-case, lower-case, a digit and a symbol."


def validate_password_strength(pw: str) -> None:
    if (len(pw) < 10 or not re.search(r"[A-Z]", pw) or not re.search(r"[a-z]", pw)
            or not re.search(r"\d", pw) or not re.search(r"[^A-Za-z0-9]", pw)):
        raise ValueError(PASSWORD_RULES)


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8")[:72], hashed.encode())
    except ValueError:
        return False


# Constant-time dummy hash to equalise timing when the user does not exist
DUMMY_HASH = hash_password("Dummy-Password-123!")


# ---------------------------------------------------------------- tokens
def create_access_token(user_id: str, role: str, hospital_id: str | None, session_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "role": role, "hid": hospital_id, "sid": session_id, "typ": "access",
               "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes), "jti": str(uuid.uuid4())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, session_id: str, expires_at: datetime) -> str:
    payload = {"sub": user_id, "sid": session_id, "typ": "refresh", "iat": datetime.now(timezone.utc), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> dict:
    data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if data.get("typ") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return data


# ---------------------------------------------------------------- RBAC
P = {
    "patients.read", "patients.write", "patients.archive", "consent.write",
    "screenings.read", "screenings.write", "images.view", "ai.run",
    "review.write", "review.sign", "reports.read", "reports.generate",
    "analytics.read", "users.manage", "hospital.manage", "branches.manage",
    "audit.read", "subscription.read", "platform.manage",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    # Platform operator: manages tenants, plans and licences. Deliberately has NO access to patient data.
    Role.SUPER_ADMIN.value: {"platform.manage", "audit.read", "subscription.read"},
    Role.HOSPITAL_ADMIN.value: {
        "patients.read", "patients.write", "patients.archive", "consent.write", "screenings.read", "screenings.write",
        "images.view", "ai.run", "reports.read", "reports.generate", "analytics.read", "users.manage",
        "hospital.manage", "branches.manage", "audit.read", "subscription.read"},
    Role.OPHTHALMOLOGIST.value: {
        "patients.read", "patients.write", "consent.write", "screenings.read", "screenings.write", "images.view",
        "ai.run", "review.write", "review.sign", "reports.read", "reports.generate", "analytics.read"},
    Role.TECHNICIAN.value: {
        "patients.read", "patients.write", "consent.write", "screenings.read", "screenings.write", "images.view",
        "ai.run", "reports.read", "reports.generate"},
    Role.RECEPTIONIST.value: {"patients.read", "patients.write", "consent.write", "screenings.read", "reports.read"},
}


def has_permission(role: str, perm: str) -> bool:
    return perm in ROLE_PERMISSIONS.get(role, set())
