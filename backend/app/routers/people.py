from ..core.enums import Role
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.auth import current_user, require_role, utc
from ..models import (
    User,
    Student,
    Company,
    Team,
    TeamMember,
    Submission,
    SubmissionMember,
    PointsTransaction,
    Problem,
)
from ..schemas import TeamInput, MemberInput
from ..services.privacy import submission_dto
from ..services.problems import company_dto

router = APIRouter(tags=["Students and teams"])


def team_dto(db, team):
    members = [
        {"id": s.id, "fullName": s.full_name, "university": s.university}
        for s in db.scalars(
            select(Student)
            .join(TeamMember, TeamMember.student_id == Student.id)
            .where(TeamMember.team_id == team.id)
            .order_by(Student.id)
        )
    ]
    return {
        "id": team.id,
        "name": team.name,
        "members": members,
        "locked": bool(
            db.scalar(
                select(Submission.id).where(Submission.team_id == team.id).limit(1)
            )
        ),
    }


@router.get("/students/me")
def profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, Role.STUDENT)
    s = db.get(Student, user.id)
    return {
        "id": s.id,
        "fullName": s.full_name,
        "email": user.email,
        "university": s.university,
        "specialization": s.specialization,
        "course": s.course,
        "skills": s.skills,
        "interests": s.interests,
        "githubUrl": s.github_url,
        "portfolioUrl": s.portfolio_url,
        "totalPoints": str(s.total_points),
    }


@router.get("/students/me/points")
def points(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, Role.STUDENT)
    return {
        "totalPoints": str(db.get(Student, user.id).total_points),
        "transactions": [
            {
                "id": p.id,
                "problemId": p.problem_id,
                "problemTitle": db.get(Problem, p.problem_id).title,
                "points": str(p.points),
                "reason": p.reason,
                "createdAt": utc(p.created_at).isoformat(),
            }
            for p in db.scalars(
                select(PointsTransaction)
                .where(PointsTransaction.student_id == user.id)
                .order_by(PointsTransaction.id.desc())
            )
        ],
    }


@router.get("/students/demo-directory")
def directory(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, Role.STUDENT)
    return [
        {"id": s.id, "fullName": s.full_name, "university": s.university}
        for s in db.scalars(select(Student).order_by(Student.id))
    ]


@router.get("/teams")
def teams(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, Role.STUDENT)
    return [
        team_dto(db, t)
        for t in db.scalars(
            select(Team)
            .join(TeamMember)
            .where(TeamMember.student_id == user.id)
            .order_by(Team.id)
        )
    ]


@router.post("/teams", status_code=201)
def create_team(
    request: TeamInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_role(user, Role.STUDENT)
    members = sorted(set([user.id, *request.member_ids]))
    if any(not db.get(Student, m) for m in members):
        raise HTTPException(422, "Участник не найден")
    team = Team(name=request.name)
    db.add(team)
    db.flush()
    for m in members:
        db.add(
            TeamMember(
                team_id=team.id,
                student_id=m,
                role="OWNER" if m == user.id else "MEMBER",
            )
        )
    db.commit()
    return team_dto(db, team)


@router.post("/teams/{team_id}/members", status_code=201)
def add_member(
    team_id: int,
    request: MemberInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_role(user, Role.STUDENT)
    team = db.scalar(select(Team).where(Team.id == team_id).with_for_update())
    membership = db.get(TeamMember, (team_id, user.id))
    if not team or not membership or membership.role != "OWNER":
        raise HTTPException(403, "Добавлять участников может создатель команды")
    if db.scalar(select(Submission.id).where(Submission.team_id == team_id).limit(1)):
        raise HTTPException(
            409,
            "После отправки решения состав команды зафиксирован. Создайте новую команду",
        )
    if not db.get(Student, request.student_id):
        raise HTTPException(422, "Студент не найден")
    if not db.get(TeamMember, (team_id, request.student_id)):
        db.add(TeamMember(team_id=team_id, student_id=request.student_id))
        db.commit()
    return team_dto(db, team)


@router.get("/students/me/submissions")
def my_submissions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, Role.STUDENT)
    submissions = db.scalars(
        select(Submission)
        .join(SubmissionMember)
        .where(SubmissionMember.student_id == user.id)
        .order_by(Submission.created_at.desc())
    )
    return [
        {
            **submission_dto(db, s, True),
            "problemTitle": db.get(Problem, s.problem_id).title,
            "deadline": utc(db.get(Problem, s.problem_id).deadline).isoformat(),
        }
        for s in submissions
    ]


@router.get("/company/me")
def company(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, Role.COMPANY)
    return company_dto(db.scalar(select(Company).where(Company.user_id == user.id)))
