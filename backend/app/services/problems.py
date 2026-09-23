from ..core.enums import Role, ProblemStatus
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select, func, delete
from ..models import (
    Company,
    Problem,
    ProblemRevision,
    ProblemScore,
    Submission,
    Question,
    Answer,
    Comment,
    now,
)
from ..core.auth import utc, require_role
from ..schemas import ProblemInput, CardDraft, QUALITY_WEIGHTS
from .ai.problem_scorer import score
from .moderation import record_moderation
from .privacy import submission_dto, identity_terms, scrub


def get_problem(db, problem_id, user=None, owner=False, lock=False):
    query = select(Problem).where(Problem.id == problem_id)
    problem = db.scalar(query.with_for_update() if lock else query)
    if problem is None:
        raise HTTPException(404, "Задача не найдена")
    company = db.get(Company, problem.company_id)
    is_owner = user and user.role == Role.COMPANY and user.id == company.user_id
    if owner and not is_owner:
        raise HTTPException(403, "Доступно только компании-владельцу")
    if (problem.hidden or problem.status == ProblemStatus.DRAFT) and not (
        is_owner or (user and user.role == Role.ADMIN)
    ):
        raise HTTPException(404, "Задача не найдена")
    return problem


def card_from_problem(problem):
    return CardDraft(
        **{field: getattr(problem, field) for field in CardDraft.model_fields}
    )


def update_quality(db, problem):
    analysis = score(card_from_problem(problem))
    problem.quality_score = analysis.overall_score
    problem.ai_source = analysis.source
    db.execute(delete(ProblemScore).where(ProblemScore.problem_id == problem.id))
    for key, criterion in analysis.criteria.items():
        db.add(
            ProblemScore(
                problem_id=problem.id,
                criterion=key,
                analysis=criterion.model_dump(by_alias=True),
            )
        )


def ensure_open(problem):
    if (
        problem.hidden
        or problem.status != ProblemStatus.PUBLISHED
        or problem.winner_submission_id
        or now() >= utc(problem.deadline)
    ):
        raise HTTPException(409, "Приём решений закрыт")


def company_dto(company):
    return {
        "id": company.id,
        "name": company.name,
        "description": company.description,
        "industry": company.industry,
        "city": company.city,
        "email": company.email,
        "telegram": company.telegram,
    }


def problem_dto(db, problem, detail=False):
    company = db.get(Company, problem.company_id)
    expired = now() >= utc(problem.deadline)
    effective_status = (
        ProblemStatus.CLOSED
        if problem.status == ProblemStatus.PUBLISHED and expired
        else problem.status
    )
    data = dict(
        id=problem.id,
        company=company_dto(company),
        title=problem.title,
        industry=problem.industry,
        context=problem.context,
        qualityScore=problem.quality_score,
        readiness=(
            "PRIORITY"
            if problem.quality_score >= 90
            else (
                "READY"
                if problem.quality_score >= 70
                else "WORKING" if problem.quality_score >= 40 else "NEEDS_CLARIFICATION"
            )
        ),
        deadline=utc(problem.deadline).isoformat(),
        status=effective_status,
        acceptingSubmissions=effective_status == ProblemStatus.PUBLISHED
        and not problem.hidden,
        submissionCount=db.scalar(
            select(func.count())
            .select_from(Submission)
            .where(Submission.problem_id == problem.id, Submission.hidden == False)
        ),
        winnerSubmissionId=problem.winner_submission_id,
        companyScore=problem.company_score,
        feedback=problem.feedback,
        updatedAt=utc(problem.updated_at).isoformat(),
        hidden=problem.hidden,
        completed=problem.company_score is not None,
    )
    if detail:
        terms = identity_terms(db) if not problem.winner_submission_id else []
        public_text = lambda value: scrub(value, terms) if terms else value
        data.update(card_from_problem(problem).model_dump(by_alias=True))
        breakdown = {
            s.criterion: s.analysis
            for s in db.scalars(
                select(ProblemScore).where(ProblemScore.problem_id == problem.id)
            )
        }
        data["qualityAnalysis"] = {
            "overallScore": problem.quality_score,
            "source": problem.ai_source,
            "criteria": {
                key: breakdown[key] for key in QUALITY_WEIGHTS if key in breakdown
            },
        }
        data["revisions"] = [
            {
                "id": r.id,
                "changedFields": r.changed_fields,
                "previousValues": r.previous_values,
                "newValues": r.new_values,
                "createdAt": utc(r.created_at).isoformat(),
            }
            for r in db.scalars(
                select(ProblemRevision)
                .where(ProblemRevision.problem_id == problem.id)
                .order_by(ProblemRevision.id.desc())
            )
        ]
        data["questions"] = [
            {
                "id": q.id,
                "text": public_text(q.text),
                "author": "Участник",
                "createdAt": utc(q.created_at).isoformat(),
                "answers": [
                    {
                        "id": a.id,
                        "text": public_text(a.text),
                        "author": company.name,
                        "createdAt": utc(a.created_at).isoformat(),
                    }
                    for a in db.scalars(
                        select(Answer)
                        .where(Answer.question_id == q.id, Answer.hidden == False)
                        .order_by(Answer.id)
                    )
                ],
            }
            for q in db.scalars(
                select(Question)
                .where(Question.problem_id == problem.id, Question.hidden == False)
                .order_by(Question.id)
            )
        ]
        data["comments"] = [
            {
                "id": c.id,
                "text": c.text,
                "author": "Участник",
                "createdAt": utc(c.created_at).isoformat(),
            }
            for c in db.scalars(
                select(Comment)
                .where(Comment.problem_id == problem.id, Comment.hidden == False)
                .order_by(Comment.id)
            )
        ]
        winner = (
            db.get(Submission, problem.winner_submission_id)
            if problem.winner_submission_id and problem.company_score is not None
            else None
        )
        # The public endpoint exposes only the winner, after business scoring.
        # Public identity uses the same deliberate reveal policy as company review.
        data["winner"] = (
            submission_dto(db, winner, True) if winner and not winner.hidden else None
        )
    return data


def create_problem(db, user, request):
    require_role(user, Role.COMPANY)
    company = db.scalar(select(Company).where(Company.user_id == user.id))
    if utc(request.deadline) <= now():
        raise HTTPException(422, "Выберите будущий дедлайн")
    problem = Problem(company_id=company.id, **request.model_dump())
    db.add(problem)
    db.flush()
    update_quality(db, problem)
    record_moderation(db, "problem", problem.id, problem.title + " " + problem.context)
    db.commit()
    return problem_dto(db, problem, True)


def edit_problem(db, user, problem_id, patch):
    problem = get_problem(db, problem_id, user, owner=True, lock=True)
    if problem.winner_submission_id:
        raise HTTPException(409, "После выбора победителя задача зафиксирована")
    changes = patch.model_dump(exclude_unset=True)
    merged = {key: getattr(problem, key) for key in ProblemInput.model_fields}
    merged["deadline"] = utc(problem.deadline)
    try:
        validated = ProblemInput.model_validate({**merged, **changes})
    except ValueError:
        raise HTTPException(422, "Проверьте заполненные поля и часовой пояс дедлайна")
    if "deadline" in changes and utc(validated.deadline) != utc(problem.deadline):
        if utc(problem.deadline) <= now() or utc(validated.deadline) <= now():
            raise HTTPException(
                409, "Истёкший дедлайн нельзя перенести или открыть заново"
            )
    old, new = {}, {}
    for key in changes:
        value = getattr(validated, key)
        before = getattr(problem, key)
        if key == "deadline":
            before = utc(before)
        if before != value:
            old[key] = before.isoformat() if hasattr(before, "isoformat") else before
            new[key] = value.isoformat() if hasattr(value, "isoformat") else value
            setattr(problem, key, value)
    if new:
        db.add(
            ProblemRevision(
                problem_id=problem.id,
                changed_fields=list(new),
                previous_values=old,
                new_values=new,
            )
        )
        problem.updated_at = now()
        update_quality(db, problem)
        record_moderation(
            db, "problem", problem.id, " ".join(str(v) for v in new.values())
        )
    db.commit()
    return problem_dto(db, problem, True)
