from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Hospital, User, UserSession
from .security import decode_token, has_permission

bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user: User, session_id: str):
        self.user = user
        self.session_id = session_id

    @property
    def id(self): return self.user.id

    @property
    def role(self): return self.user.role

    @property
    def hospital_id(self): return self.user.hospital_id

    def can(self, perm: str) -> bool:
        return has_permission(self.user.role, perm)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else ""))[:64]


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> CurrentUser:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        data = decode_token(creds.credentials, "access")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    sess = db.get(UserSession, data.get("sid"))
    if not sess or sess.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session revoked")
    user = db.get(User, data["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account disabled")
    if user.hospital_id:
        h = db.get(Hospital, user.hospital_id)
        if not h or not h.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Hospital account is inactive")
    return CurrentUser(user, sess.id)


def require(*perms: str):
    def _dep(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        for p in perms:
            if not cu.can(p):
                raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role does not permit this action ({p})")
        return cu
    return _dep


def tenant_id(cu: CurrentUser) -> str:
    """Hospital scope for PHI queries. Super-admins have no hospital and therefore no PHI access."""
    if not cu.hospital_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Patient data is only accessible to hospital staff")
    return cu.hospital_id


def get_owned(db: Session, model, obj_id: str, hospital_id: str):
    """Fetch a tenant-owned row; returns 404 (not 403) for other tenants' rows to avoid leaking existence."""
    obj = db.get(model, obj_id)
    if obj is None or getattr(obj, "hospital_id", None) != hospital_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj


def check_licence(db: Session, hospital_id: str) -> Hospital:
    h = db.get(Hospital, hospital_id)
    if h.licence_status in ("suspended", "expired"):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"Licence is {h.licence_status}. Contact NetraRakshak support.")
    if h.licence_expires_at:
        exp = h.licence_expires_at if h.licence_expires_at.tzinfo else h.licence_expires_at.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Licence has expired. Contact NetraRakshak support.")
    return h
