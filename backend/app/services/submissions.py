from ..core.enums import Role, ProblemStatus, SubmissionStatus
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import select, func, update
from ..core.auth import require_role
from ..models import (
    Submission,
    Team,
    TeamMember,
    SubmissionMember,
    SubmissionChat,
    SubmissionReview,
    Problem,
    Student,
    PointsTransaction,
    now,
)
from .problems import get_problem, ensure_open, card_from_problem, problem_dto
from .privacy import submission_dto, identity_terms, scrub
from .ai.solution_evaluator import evaluate
from .moderation import record_moderation


def check_member(db, user, submission):
    require_role(user, Role.STUDENT)
    if db.get(SubmissionMember, (submission.id, user.id)) is None:
        raise HTTPException(403, "Решение принадлежит другой команде")


def accessible_submission(db, user, submission_id):
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(404, "Решение не найдено")
    problem = get_problem(db, submission.problem_id, user)
    if user.role == Role.COMPANY:
        get_problem(db, problem.id, user, owner=True)
    elif user.role == Role.STUDENT:
        check_member(db, user, submission)
    else:
        raise HTTPException(403, "Чат доступен только бизнесу и авторам решения")
    if submission.hidden:
        raise HTTPException(404, "Решение скрыто модератором")
    return submission, problem


def save_submission(db, user, problem_id, request, submission_id=None):
    require_role(user, Role.STUDENT)
    problem = get_problem(db, problem_id, user, lock=True)
    ensure_open(problem)
    # Coordinate roster freezing with concurrent add-member requests.
    db.scalar(select(Team).where(Team.id == request.team_id).with_for_update())
    if not db.get(TeamMember, (request.team_id, user.id)):
        raise HTTPException(403, "Вы не состоите в этой команде")
    if submission_id:
        submission = db.get(Submission, submission_id)
        if not submission or submission.problem_id != problem_id:
            raise HTTPException(404, "Решение не найдено")
        check_member(db, user, submission)
        if request.team_id != submission.team_id or submission.hidden:
            raise HTTPException(
                409,
                "Нельзя менять авторов отправленной работы или редактировать скрытую работу",
            )
        for key, value in request.model_dump().items():
            setattr(submission, key, value)
        submission.updated_at = now()
    else:
        if db.scalar(
            select(Submission.id).where(
                Submission.problem_id == problem_id,
                Submission.team_id == request.team_id,
            )
        ):
            raise HTTPException(
                409, "Команда уже отправила решение; откройте его для редактирования"
            )
        number = (
            db.scalar(
                select(func.max(Submission.anonymous_number)).where(
                    Submission.problem_id == problem_id
                )
            )
            or 0
        ) + 1
        submission = Submission(
            problem_id=problem_id, anonymous_number=number, **request.model_dump()
        )
        db.add(submission)
        db.flush()
        for member in db.scalars(
            select(TeamMember).where(TeamMember.team_id == request.team_id)
        ):
            db.add(
                SubmissionMember(
                    submission_id=submission.id, student_id=member.student_id
                )
            )
        db.add(SubmissionChat(submission_id=submission.id))
    safe_material = scrub(
        request.model_dump(
            by_alias=True,
            exclude={"team_id", "demo_url", "repository_url", "project_file_name"},
        ),
        identity_terms(db),
    )
    analysis = evaluate(
        card_from_problem(problem).model_dump(by_alias=True), safe_material
    )
    existing = db.get(SubmissionReview, submission.id)
    if existing:
        existing.analysis = analysis.model_dump(by_alias=True)
    else:
        db.add(
            SubmissionReview(
                submission_id=submission.id, analysis=analysis.model_dump(by_alias=True)
            )
        )
    record_moderation(
        db,
        "submission",
        submission.id,
        submission.summary
        + " "
        + submission.solution_description
        + " "
        + submission.implementation_details,
    )
    # AI can take time: reject an operation that crossed the deadline before commit.
    ensure_open(problem)
    db.commit()
    return submission_dto(db, submission, True)


def select_winner(db, user, problem_id, submission_id):
    problem = get_problem(db, problem_id, user, owner=True, lock=True)
    from ..core.auth import utc

    if now() < utc(problem.deadline) or problem.status == ProblemStatus.DRAFT:
        raise HTTPException(409, "Победителя можно выбрать только после дедлайна")
    if problem.hidden:
        raise HTTPException(409, "Задача скрыта модератором")
    if problem.winner_submission_id:
        if problem.winner_submission_id == submission_id:
            return problem_dto(db, problem, True)
        raise HTTPException(409, "Победитель уже выбран. Изменить выбор нельзя")
    submission = db.get(Submission, submission_id)
    if not submission or submission.problem_id != problem.id or submission.hidden:
        raise HTTPException(422, "Выберите доступное решение этой задачи")
    result = db.execute(
        update(Problem)
        .where(Problem.id == problem.id, Problem.winner_submission_id.is_(None))
        .values(
            winner_submission_id=submission.id,
            status=ProblemStatus.CLOSED,
            closed_at=now(),
        )
    )
    if result.rowcount != 1:
        raise HTTPException(409, "Победитель уже выбран другим запросом")
    db.execute(
        update(Submission)
        .where(Submission.problem_id == problem.id)
        .values(status=SubmissionStatus.NOT_SELECTED)
    )
    submission.status = SubmissionStatus.WINNER
    db.commit()
    db.refresh(problem)
    return problem_dto(db, problem, True)


def award_score(db, user, problem_id, request):
    problem = get_problem(db, problem_id, user, owner=True, lock=True)
    if not problem.winner_submission_id:
        raise HTTPException(409, "Сначала выберите победителя")
    if problem.company_score is not None:
        if problem.company_score != request.score:
            raise HTTPException(409, "Оценка уже выставлена и не может быть изменена")
        return {"problem": problem_dto(db, problem, True), "alreadyAwarded": True}
    members = list(
        db.scalars(
            select(SubmissionMember).where(
                SubmissionMember.submission_id == problem.winner_submission_id
            )
        )
    )
    if not members:
        raise HTTPException(409, "В решении отсутствует состав команды")
    result = db.execute(
        update(Problem)
        .where(Problem.id == problem.id, Problem.company_score.is_(None))
        .values(company_score=request.score, feedback=request.feedback)
    )
    if result.rowcount != 1:
        raise HTTPException(
            409, "Оценка уже сохранена другим запросом; обновите страницу"
        )
    share = (Decimal(request.score) / Decimal(len(members))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    # All ledger entries and balance increments share one DB transaction.
    for member in members:
        db.add(
            PointsTransaction(
                student_id=member.student_id,
                problem_id=problem.id,
                submission_id=problem.winner_submission_id,
                points=share,
            )
        )
        db.execute(
            update(Student)
            .where(Student.id == member.student_id)
            .values(total_points=Student.total_points + share)
        )
    db.commit()
    db.refresh(problem)
    return {
        "problem": problem_dto(db, problem, True),
        "alreadyAwarded": False,
        "pointsPerStudent": str(share),
    }
