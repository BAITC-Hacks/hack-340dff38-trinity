from ..core.enums import Role
import hashlib
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.config import settings
from ..core.auth import current_user
from ..models import User, Company, Student, DemoSession, now
from ..schemas import LoginInput

router = APIRouter(prefix="/auth", tags=["Demo authentication"])


def user_dto(db, user):
    company = (
        db.scalar(select(Company).where(Company.user_id == user.id))
        if user.role == Role.COMPANY
        else None
    )
    student = db.get(Student, user.id) if user.role == Role.STUDENT else None
    return {
        "id": user.id,
        "role": user.role,
        "email": user.email,
        "name": (
            company.name
            if company
            else student.full_name if student else "Администратор"
        ),
        "companyId": company.id if company else None,
    }


@router.get("/demo-accounts")
def accounts(db: Session = Depends(get_db)):
    if not settings().demo_auth_enabled:
        raise HTTPException(403, "Демо-вход отключён")
    return {
        "accounts": [
            user_dto(db, u) for u in db.scalars(select(User).order_by(User.id))
        ],
        "accessCodeRequired": bool(settings().demo_access_code),
    }


@router.post("/demo-login")
def login(request: LoginInput, db: Session = Depends(get_db)):
    cfg = settings()
    if not cfg.demo_auth_enabled:
        raise HTTPException(403, "Демо-вход отключён")
    if cfg.demo_access_code and not secrets.compare_digest(
        request.access_code, cfg.demo_access_code
    ):
        raise HTTPException(403, "Неверный код доступа к демонстрации")
    user = db.get(User, request.user_id)
    if not user:
        raise HTTPException(404, "Демо-аккаунт не найден")
    token = secrets.token_urlsafe(32)
    db.add(
        DemoSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=now() + timedelta(hours=24),
        )
    )
    db.commit()
    return {"token": token, "user": user_dto(db, user), "demoOnly": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_dto(db, user)
