from ..core.enums import Role, ModerationStatus
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.auth import current_user, require_role, utc
from ..models import (
    User,
    Problem,
    Submission,
    Student,
    Company,
    ModerationItem,
    Question,
    Answer,
    Comment,
)

router = APIRouter(prefix="/admin", tags=["Moderation"])


@router.get("/moderation")
def queue(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, Role.ADMIN)
    counts = {
        key: db.scalar(select(func.count()).select_from(model))
        for key, model in [
            ("problems", Problem),
            ("students", Student),
            ("companies", Company),
            ("submissions", Submission),
        ]
    }
    items = [
        {
            "id": m.id,
            "entityType": m.entity_type,
            "entityId": m.entity_id,
            "status": m.status,
            "reasons": m.reasons,
            "excerpt": m.excerpt,
            "source": m.ai_source,
            "createdAt": utc(m.created_at).isoformat(),
        }
        for m in db.scalars(select(ModerationItem).order_by(ModerationItem.id.desc()))
    ]
    return {"counts": counts, "items": items}


def decide(db, user, item_id, hidden):
    require_role(user, Role.ADMIN)
    item = db.get(ModerationItem, item_id)
    if not item:
        raise HTTPException(404, "Запись модерации не найдена")
    models = {
        "problem": Problem,
        "submission": Submission,
        "question": Question,
        "answer": Answer,
        "comment": Comment,
    }
    entity = db.get(
        models[item.entity_type],
        item.entity_id if item.entity_type == "submission" else int(item.entity_id),
    )
    entity.hidden = hidden
    item.status = ModerationStatus.HIDDEN if hidden else ModerationStatus.APPROVED
    db.commit()
    return {"id": item.id, "status": item.status}


@router.post("/moderation/{item_id}/approve")
def approve(
    item_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return decide(db, user, item_id, False)


@router.post("/moderation/{item_id}/hide")
def hide(
    item_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return decide(db, user, item_id, True)
