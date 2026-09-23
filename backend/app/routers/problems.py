from ..core.enums import Role, ProblemStatus
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.auth import current_user, optional_user, require_role, utc
from ..core.config import settings
from ..models import (
    Problem,
    Company,
    User,
    Submission,
    Question,
    Answer,
    Comment,
    ProblemRevision,
    now,
)
from ..schemas import (
    ProblemInput,
    ProblemPatch,
    TextInput,
    WinnerInput,
    WinnerScoreInput,
)
from ..services.problems import get_problem, problem_dto, create_problem, edit_problem
from ..services.submissions import select_winner, award_score
from ..services.privacy import submission_dto
from ..services.moderation import record_moderation

router = APIRouter(tags=["Problems"])


@router.get("/problems")
def catalog(
    industry: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    query = select(Problem).where(
        Problem.status != ProblemStatus.DRAFT, Problem.hidden == False
    )
    if industry:
        query = query.where(Problem.industry == industry)
    problems = db.scalars(
        query.order_by(Problem.quality_score.desc(), Problem.id.desc())
    ).all()
    industries = db.scalars(
        select(Problem.industry)
        .where(Problem.status != ProblemStatus.DRAFT, Problem.hidden == False)
        .distinct()
        .order_by(Problem.industry)
    ).all()
    return {"items": [problem_dto(db, p) for p in problems], "industries": industries}


@router.get("/problems/{problem_id}")
def detail(
    problem_id: int,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    return problem_dto(db, get_problem(db, problem_id, user), True)


@router.post("/problems", status_code=201)
def create(
    request: ProblemInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return create_problem(db, user, request)


@router.patch("/problems/{problem_id}")
def edit(
    problem_id: int,
    request: ProblemPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return edit_problem(db, user, problem_id, request)


@router.post("/problems/{problem_id}/publish")
def publish(
    problem_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    p = get_problem(db, problem_id, user, owner=True, lock=True)
    if p.hidden or p.winner_submission_id or utc(p.deadline) <= now():
        raise HTTPException(409, "Проверьте дедлайн и статус модерации задачи")
    p.status = ProblemStatus.PUBLISHED
    p.published_at = p.published_at or now()
    db.commit()
    return problem_dto(db, p, True)


@router.get("/company/problems")
def company_problems(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, Role.COMPANY)
    company = db.scalar(select(Company).where(Company.user_id == user.id))
    return [
        problem_dto(db, p)
        for p in db.scalars(
            select(Problem)
            .where(Problem.company_id == company.id)
            .order_by(Problem.id.desc())
        )
    ]


@router.get("/company/problems/{problem_id}/submissions")
def review(
    problem_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    p = get_problem(db, problem_id, user, owner=True)
    return {
        "problem": problem_dto(db, p, True),
        "items": [
            submission_dto(db, s, bool(p.winner_submission_id))
            for s in db.scalars(
                select(Submission)
                .where(Submission.problem_id == p.id, Submission.hidden == False)
                .order_by(Submission.anonymous_number)
            )
        ],
    }


@router.post("/problems/{problem_id}/select-winner")
def winner(
    problem_id: int,
    request: WinnerInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return select_winner(db, user, problem_id, request.submission_id)


@router.post("/problems/{problem_id}/winner-score")
def score_winner(
    problem_id: int,
    request: WinnerScoreInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return award_score(db, user, problem_id, request)


@router.post("/problems/{problem_id}/questions", status_code=201)
def question(
    problem_id: int,
    request: TextInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_role(user, Role.STUDENT, Role.COMPANY)
    p = get_problem(db, problem_id, user)
    if p.status == ProblemStatus.DRAFT or p.hidden:
        raise HTTPException(409, "Обсуждение доступно для опубликованных задач")
    q = Question(problem_id=p.id, author_id=user.id, text=request.text)
    db.add(q)
    db.flush()
    record_moderation(db, "question", q.id, q.text)
    db.commit()
    return {"id": q.id}


@router.post("/questions/{question_id}/answers", status_code=201)
def answer(
    question_id: int,
    request: TextInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.get(Question, question_id)
    if not q or q.hidden:
        raise HTTPException(404, "Вопрос не найден")
    get_problem(db, q.problem_id, user, owner=True)
    a = Answer(question_id=q.id, author_id=user.id, text=request.text)
    db.add(a)
    db.flush()
    record_moderation(db, "answer", a.id, a.text)
    db.commit()
    return {"id": a.id}


@router.post("/problems/{problem_id}/comments", status_code=201)
def comment(
    problem_id: int,
    request: TextInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_role(user, Role.STUDENT, Role.COMPANY)
    p = get_problem(db, problem_id, user)
    if p.company_score is None:
        raise HTTPException(409, "Комментарии откроются после оценки победителя")
    c = Comment(problem_id=p.id, author_id=user.id, text=request.text)
    db.add(c)
    db.flush()
    record_moderation(db, "comment", c.id, c.text)
    db.commit()
    return {"id": c.id}


@router.post("/demo/problems/{problem_id}/expire")
def expire(
    problem_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if not settings().demo_tools_enabled:
        raise HTTPException(404, "Демо-инструменты отключены")
    p = get_problem(db, problem_id, user, owner=True, lock=True)
    if (
        p.status != ProblemStatus.PUBLISHED
        or p.winner_submission_id
        or utc(p.deadline) <= now()
    ):
        raise HTTPException(409, "Приём уже закрыт или задача не опубликована")
    old = utc(p.deadline).isoformat()
    p.deadline = now()
    p.status = ProblemStatus.CLOSED
    p.closed_at = now()
    p.updated_at = now()
    db.add(
        ProblemRevision(
            problem_id=p.id,
            changed_fields=["deadline"],
            previous_values={"deadline": old},
            new_values={
                "deadline": p.deadline.isoformat(),
                "reason": "Демонстрация завершения приёма",
            },
        )
    )
    db.commit()
    return problem_dto(db, p, True)
