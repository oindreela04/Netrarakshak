from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..config import get_settings
from ..database import get_db
from ..deps import CurrentUser, client_ip, get_current_user
from ..models import Hospital, User, UserSession
from ..security import (DUMMY_HASH, ROLE_PERMISSIONS, create_access_token, create_refresh_token, decode_token,
                        hash_password, validate_password_strength, verify_password)
from ..serializers import hospital_out, iso, user_out

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


def _aware(dt):
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _issue(db: Session, user: User, request: Request) -> dict:
    exp = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    sess = UserSession(user_id=user.id, expires_at=exp, ip_address=client_ip(request),
                       user_agent=(request.headers.get("user-agent") or "")[:300])
    db.add(sess)
    db.flush()
    return {"access_token": create_access_token(user.id, user.role, user.hospital_id, sess.id),
            "refresh_token": create_refresh_token(user.id, sess.id, exp), "token_type": "bearer",
            "expires_in": settings.access_token_minutes * 60}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == body.email.lower())).scalar_one_or_none()
    ip = client_ip(request)
    generic = HTTPException(401, "Incorrect email or password")
    if not user:
        verify_password(body.password, DUMMY_HASH)
        audit.record(db, "auth.login_failed", ip=ip, details={"email": body.email.lower(), "reason": "unknown_user"})
        raise generic
    now = datetime.now(timezone.utc)
    if user.locked_until and _aware(user.locked_until) > now:
        audit.record(db, "auth.login_locked", user=user, ip=ip)
        raise HTTPException(423, "Account temporarily locked after repeated failed attempts. Try again later.")
    if not verify_password(body.password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_logins = 0
        audit.record(db, "auth.login_failed", user=user, ip=ip, details={"reason": "bad_password"})
        raise generic
    if not user.is_active:
        audit.record(db, "auth.login_inactive", user=user, ip=ip)
        raise HTTPException(403, "Account is disabled")
    if user.hospital_id:
        h = db.get(Hospital, user.hospital_id)
        if not h.is_active:
            raise HTTPException(403, "Hospital account is inactive")
    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now
    tokens = _issue(db, user, request)
    audit.record(db, "auth.login", user=user, ip=ip)
    return tokens


@router.post("/refresh")
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db)):
    try:
        data = decode_token(body.refresh_token, "refresh")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid refresh token")
    sess = db.get(UserSession, data["sid"])
    if not sess or sess.revoked_at or _aware(sess.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(401, "Session expired")
    user = db.get(User, data["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "Account disabled")
    # rotate: revoke old session, issue new
    sess.revoked_at = datetime.now(timezone.utc)
    tokens = _issue(db, user, request)
    db.commit()
    return tokens


@router.post("/logout")
def logout(request: Request, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    sess = db.get(UserSession, cu.session_id)
    sess.revoked_at = datetime.now(timezone.utc)
    audit.record(db, "auth.logout", user=cu, ip=client_ip(request))
    return {"ok": True}


@router.get("/me")
def me(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.get(Hospital, cu.hospital_id) if cu.hospital_id else None
    return {"user": user_out(cu.user), "hospital": hospital_out(h, full=False) if h else None,
            "permissions": sorted(ROLE_PERMISSIONS.get(cu.role, set()))}


@router.post("/change-password")
def change_password(body: ChangePasswordIn, request: Request, cu: CurrentUser = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(body.current_password, cu.user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise HTTPException(422, str(e))
    cu.user.password_hash = hash_password(body.new_password)
    cu.user.must_change_password = False
    now = datetime.now(timezone.utc)
    for s in db.execute(select(UserSession).where(UserSession.user_id == cu.id, UserSession.revoked_at.is_(None),
                                                  UserSession.id != cu.session_id)).scalars():
        s.revoked_at = now  # sign out other devices
    audit.record(db, "auth.password_changed", user=cu, ip=client_ip(request))
    return {"ok": True}


@router.get("/sessions")
def sessions(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(UserSession).where(UserSession.user_id == cu.id, UserSession.revoked_at.is_(None))
                      .order_by(UserSession.created_at.desc())).scalars()
    now = datetime.now(timezone.utc)
    return [{"id": s.id, "created_at": iso(s.created_at), "expires_at": iso(s.expires_at), "ip_address": s.ip_address,
             "user_agent": s.user_agent, "current": s.id == cu.session_id} for s in rows if _aware(s.expires_at) > now]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: str, request: Request, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(UserSession, session_id)
    if not s or s.user_id != cu.id:
        raise HTTPException(404, "Session not found")
    s.revoked_at = datetime.now(timezone.utc)
    audit.record(db, "auth.session_revoked", user=cu, ip=client_ip(request), entity_type="session", entity_id=session_id)
    return {"ok": True}
