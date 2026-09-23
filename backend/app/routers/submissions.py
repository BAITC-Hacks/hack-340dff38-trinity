from ..core.enums import Role
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.auth import current_user, utc
from ..models import User, Submission, SubmissionChat, Message
from ..schemas import SubmissionInput, TextInput
from ..services.submissions import save_submission, accessible_submission
from ..services.privacy import scrub, identity_terms, submission_dto

router = APIRouter(tags=["Submissions and anonymous chat"])


@router.post("/problems/{problem_id}/submissions", status_code=201)
def submit(
    problem_id: int,
    request: SubmissionInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return save_submission(db, user, problem_id, request)


@router.patch("/submissions/{submission_id}")
def edit(
    submission_id: str,
    request: SubmissionInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    s = db.get(Submission, submission_id)
    if not s:
        raise HTTPException(404, "Решение не найдено")
    return save_submission(db, user, s.problem_id, request, submission_id)


@router.get("/submissions/{submission_id}")
def get_one(
    submission_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    s, p = accessible_submission(db, user, submission_id)
    return submission_dto(
        db, s, user.role == Role.STUDENT or bool(p.winner_submission_id)
    )


@router.get("/submissions/{submission_id}/messages")
def messages(
    submission_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    s, p = accessible_submission(db, user, submission_id)
    chat = db.scalar(select(SubmissionChat).where(SubmissionChat.submission_id == s.id))
    terms = (
        identity_terms(db)
        if user.role == Role.COMPANY and not p.winner_submission_id
        else []
    )
    return [
        {
            "id": m.id,
            "text": scrub(m.text, terms) if terms else m.text,
            "sender": (
                "Business representative"
                if m.sender_type == Role.COMPANY
                else f"Representative of Solution #{s.anonymous_number}"
            ),
            "isMine": m.sender_type == user.role,
            "createdAt": utc(m.created_at).isoformat(),
        }
        for m in db.scalars(
            select(Message).where(Message.chat_id == chat.id).order_by(Message.id)
        )
    ]


@router.post("/submissions/{submission_id}/messages", status_code=201)
def send(
    submission_id: str,
    request: TextInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    s, p = accessible_submission(db, user, submission_id)
    chat = db.scalar(select(SubmissionChat).where(SubmissionChat.submission_id == s.id))
    m = Message(
        chat_id=chat.id, sender_id=user.id, sender_type=user.role, text=request.text
    )
    db.add(m)
    db.commit()
    # Do not return an ORM object or sender ID, even to the sender.
    return {"id": m.id, "sent": True}
