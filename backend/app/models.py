"""Relational domain model. No identity is serialized directly from ORM objects."""

from .core.enums import ProblemStatus, SubmissionStatus, ModerationStatus
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from .core.database import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(10))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    __table_args__ = (CheckConstraint("role IN ('STUDENT','COMPANY','ADMIN')"),)


class DemoSession(Base):
    __tablename__ = "demo_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(254))
    telegram: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Student(Base):
    __tablename__ = "student_profiles"
    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(180))
    university: Mapped[str] = mapped_column(String(180), default="")
    specialization: Mapped[str] = mapped_column(String(180), default="")
    course: Mapped[int] = mapped_column(Integer, default=1)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    interests: Mapped[list] = mapped_column(JSON, default=list)
    github_url: Mapped[str] = mapped_column(String(500), default="")
    portfolio_url: Mapped[str] = mapped_column(String(500), default="")
    total_points: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("total_points >= 0"),)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TeamMember(Base):
    __tablename__ = "team_members"
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(30), default="MEMBER")


class Problem(Base):
    __tablename__ = "problems"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    context: Mapped[str] = mapped_column(Text, default="")
    need: Mapped[str] = mapped_column(Text, default="")
    users: Mapped[str] = mapped_column(Text, default="")
    available_data: Mapped[str] = mapped_column(Text, default="")
    constraints: Mapped[str] = mapped_column(Text, default="")
    expected_result: Mapped[str] = mapped_column(Text, default="")
    success_criteria: Mapped[str] = mapped_column(Text, default="")
    business_contact: Mapped[str] = mapped_column(Text, default="")
    interaction_format: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str] = mapped_column(String(120))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default=ProblemStatus.DRAFT)
    quality_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    ai_source: Mapped[str] = mapped_column(String(30), default="mock")
    winner_submission_id: Mapped[str | None] = mapped_column(
        ForeignKey("submissions.id", name="fk_problem_winner", use_alter=True),
        nullable=True,
    )
    company_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    __table_args__ = (
        CheckConstraint("quality_score BETWEEN 0 AND 100"),
        CheckConstraint("company_score IS NULL OR company_score BETWEEN 0 AND 100"),
        CheckConstraint("status IN ('DRAFT','PUBLISHED','CLOSED')"),
    )


class ProblemRevision(Base):
    __tablename__ = "problem_revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    changed_fields: Mapped[list] = mapped_column(JSON)
    previous_values: Mapped[dict] = mapped_column(JSON)
    new_values: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProblemScore(Base):
    __tablename__ = "problem_score_breakdowns"
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), primary_key=True)
    criterion: Mapped[str] = mapped_column(String(50), primary_key=True)
    analysis: Mapped[dict] = mapped_column(JSON)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text)
    solution_description: Mapped[str] = mapped_column(Text)
    implementation_details: Mapped[str] = mapped_column(Text)
    demo_url: Mapped[str] = mapped_column(String(1000), default="")
    repository_url: Mapped[str] = mapped_column(String(1000), default="")
    project_file_name: Mapped[str] = mapped_column(String(180), default="")
    anonymous_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=SubmissionStatus.SUBMITTED)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("problem_id", "team_id", name="uq_problem_team"),
        UniqueConstraint("problem_id", "anonymous_number", name="uq_anonymous_number"),
        Index(
            "uq_one_winner_per_problem",
            "problem_id",
            unique=True,
            postgresql_where=text("status = 'WINNER'"),
            sqlite_where=text("status = 'WINNER'"),
        ),
        CheckConstraint("status IN ('SUBMITTED','WINNER','NOT_SELECTED')"),
    )


class SubmissionMember(Base):
    """Frozen recipient list prevents team changes from changing score allocation."""

    __tablename__ = "submission_members"
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id"), primary_key=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id"), primary_key=True
    )


class SubmissionReview(Base):
    __tablename__ = "submission_ai_reviews"
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id"), primary_key=True
    )
    analysis: Mapped[dict] = mapped_column(JSON)


class SubmissionChat(Base):
    __tablename__ = "submission_chats"
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id"), unique=True
    )


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("submission_chats.id"), index=True)
    sender_type: Mapped[str] = mapped_column(String(10))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PointsTransaction(Base):
    __tablename__ = "points_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id"), index=True
    )
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"))
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"))
    points: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(String(180), default="Победа в бизнес-задаче")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("student_id", "problem_id", name="uq_points_once"),
        CheckConstraint("points >= 0"),
    )


class ModerationItem(Base):
    __tablename__ = "moderation_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(
        String(30), default=ModerationStatus.CLEAN, index=True
    )
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    excerpt: Mapped[str] = mapped_column(Text)
    ai_source: Mapped[str] = mapped_column(String(30), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_moderation_entity"),
    )
