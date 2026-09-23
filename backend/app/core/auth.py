import hashlib
from datetime import timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .database import get_db
from .config import settings
from ..models import DemoSession, User, now

bearer = HTTPBearer(auto_error=False)


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if credentials is None:
        return None
    if not settings().demo_auth_enabled:
        raise HTTPException(403, "Демо-вход отключён")
    session = db.get(
        DemoSession, hashlib.sha256(credentials.credentials.encode()).hexdigest()
    )
    if session is None or utc(session.expires_at) <= now():
        raise HTTPException(401, "Сессия истекла. Войдите снова")
    return db.get(User, session.user_id)


def current_user(user: User | None = Depends(optional_user)):
    if user is None:
        raise HTTPException(401, "Сначала выберите демо-аккаунт")
    return user


def require_role(user, *roles):
    if user.role not in roles:
        raise HTTPException(403, "Эта операция недоступна вашей роли")
