from ..core.enums import Role
import re
from sqlalchemy import select
from ..models import Student, User, Team, SubmissionMember, SubmissionReview
from ..schemas import AnonymousSubmissionResponse, RevealedSubmissionResponse


def scrub(value, identities):
    """Defense in depth: remove known identity, handles, URLs, email and phone numbers."""
    if isinstance(value, list):
        return [scrub(item, identities) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item, identities) for key, item in value.items()}
    if not isinstance(value, str):
        return value
    value = re.sub(
        r"(?:https?://|www\.)\S+|[\w.+-]+@[\w.-]+\.[\w-]+|@[\w.-]+",
        "[контакт скрыт]",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s]*)?",
        "[ссылка скрыта]",
        value,
        flags=re.I,
    )
    value = re.sub(r"(?:\+?\d[\d\s().-]{8,}\d)", "[номер скрыт]", value)
    for identity in sorted(set(identities), key=len, reverse=True):
        if len(identity) >= 3:
            value = re.sub(
                r"(?<!\w)" + re.escape(identity) + r"(?!\w)",
                "[автор скрыт]",
                value,
                flags=re.I,
            )
    return value


def identity_terms(db):
    terms = list(db.scalars(select(Team.name)))
    for student in db.scalars(select(Student)):
        terms.extend(
            [
                student.full_name,
                *student.full_name.split(),
                student.university,
                student.github_url,
                student.portfolio_url,
            ]
        )
    terms.extend(db.scalars(select(User.email).where(User.role == Role.STUDENT)))
    return [term for term in terms if term]


def submission_dto(db, submission, revealed=False):
    review = db.get(SubmissionReview, submission.id)
    data = dict(
        id=submission.id,
        label=f"Solution #{submission.anonymous_number}",
        anonymous_number=submission.anonymous_number,
        title=submission.title,
        summary=submission.summary,
        solution_description=submission.solution_description,
        implementation_details=submission.implementation_details,
        status=submission.status,
        ai_analysis=review.analysis if review else None,
    )
    if not revealed:
        terms = identity_terms(db)
        for key in (
            "title",
            "summary",
            "solution_description",
            "implementation_details",
            "ai_analysis",
        ):
            data[key] = scrub(data[key], terms)
        return AnonymousSubmissionResponse(**data).model_dump(
            by_alias=True, mode="json"
        )
    members = []
    for member in db.scalars(
        select(SubmissionMember).where(SubmissionMember.submission_id == submission.id)
    ):
        student = db.get(Student, member.student_id)
        user = db.get(User, member.student_id)
        members.append(
            dict(
                id=student.id,
                full_name=student.full_name,
                email=user.email,
                university=student.university,
                github_url=student.github_url,
                portfolio_url=student.portfolio_url,
            )
        )
    data.update(
        team_id=submission.team_id,
        team_name=db.get(Team, submission.team_id).name,
        members=members,
        demo_url=submission.demo_url,
        repository_url=submission.repository_url,
        project_file_name=submission.project_file_name,
        problem_id=submission.problem_id,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )
    return RevealedSubmissionResponse(**data).model_dump(by_alias=True, mode="json")
