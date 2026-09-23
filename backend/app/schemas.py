from datetime import datetime
from typing import Annotated, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


Short = Annotated[str, Field(max_length=180)]
Long = Annotated[str, Field(max_length=8000)]


class LoginInput(Schema):
    user_id: int
    access_code: str = Field(default="", max_length=200)


class ProblemInput(Schema):
    title: str = Field(min_length=3, max_length=180)
    context: Long = ""
    need: Long = ""
    users: Long = ""
    available_data: Long = ""
    constraints: Long = ""
    expected_result: Long = ""
    success_criteria: Long = ""
    business_contact: Long = ""
    interaction_format: Long = ""
    industry: str = Field(min_length=1, max_length=120)
    deadline: datetime

    @field_validator("deadline")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("Передайте дедлайн с часовым поясом")
        return value


class ProblemPatch(Schema):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    context: Long | None = None
    need: Long | None = None
    users: Long | None = None
    available_data: Long | None = None
    constraints: Long | None = None
    expected_result: Long | None = None
    success_criteria: Long | None = None
    business_contact: Long | None = None
    interaction_format: Long | None = None
    industry: str | None = Field(default=None, min_length=1, max_length=120)
    deadline: datetime | None = None


class SubmissionInput(Schema):
    team_id: int
    title: str = Field(min_length=3, max_length=180)
    summary: str = Field(min_length=10, max_length=3000)
    solution_description: str = Field(min_length=20, max_length=12000)
    implementation_details: str = Field(min_length=20, max_length=12000)
    demo_url: str = Field(default="", max_length=1000)
    repository_url: str = Field(default="", max_length=1000)
    project_file_name: Short = ""

    @field_validator("demo_url", "repository_url")
    @classmethod
    def safe_url(cls, value):
        if value and not str(HttpUrl(value)).startswith(("https://", "http://")):
            raise ValueError("Разрешены только HTTP(S) ссылки")
        return value


class TeamInput(Schema):
    name: str = Field(min_length=2, max_length=120)
    member_ids: list[int] = Field(default_factory=list, max_length=9)


class MemberInput(Schema):
    student_id: int


class TextInput(Schema):
    text: str = Field(min_length=1, max_length=3000)


class WinnerInput(Schema):
    submission_id: str = Field(min_length=36, max_length=36)


class WinnerScoreInput(Schema):
    score: int = Field(ge=0, le=100, strict=True)
    feedback: str = Field(default="", max_length=3000)


class InterviewInput(Schema):
    description: str = Field(min_length=10, max_length=8000)
    answers: dict[str, str] = Field(default_factory=dict, max_length=12)

    @field_validator("answers")
    @classmethod
    def limit_answers(cls, value):
        if any(len(k) > 50 or len(v) > 4000 for k, v in value.items()):
            raise ValueError("Слишком длинный ответ")
        return value


class CardDraft(Schema):
    title: Short = ""
    context: Long = ""
    need: Long = ""
    users: Long = ""
    available_data: Long = ""
    constraints: Long = ""
    expected_result: Long = ""
    success_criteria: Long = ""
    business_contact: Long = ""
    interaction_format: Long = ""
    industry: str = Field(default="", max_length=120)


class Clarification(Schema):
    id: str
    question: str


class InterviewResult(Schema):
    questions: list[Clarification] = Field(min_length=3, max_length=12)
    draft: CardDraft
    missing_fields: list[str]
    source: str = "mock"


class Criterion(Schema):
    score: int = Field(ge=0, le=25)
    max_score: int = Field(ge=1, le=25)
    reasoning: str = Field(max_length=3000)
    missing: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def bound_score(self):
        if self.score > self.max_score:
            raise ValueError("Score exceeds maximum")
        return self


QUALITY_WEIGHTS = {
    "context": 20,
    "data": 20,
    "result": 15,
    "success": 15,
    "constraints": 10,
    "users": 10,
    "communication": 10,
}


class QualityAnalysis(Schema):
    criteria: dict[str, Criterion]
    overall_score: int = Field(ge=0, le=100)
    source: str = "mock"

    @model_validator(mode="after")
    def check_formula(self):
        if set(self.criteria) != set(QUALITY_WEIGHTS):
            raise ValueError("Exactly seven quality criteria required")
        if any(
            self.criteria[key].max_score != weight
            for key, weight in QUALITY_WEIGHTS.items()
        ):
            raise ValueError("Invalid quality weights")
        if self.overall_score != sum(c.score for c in self.criteria.values()):
            raise ValueError("Invalid quality total")
        return self


class SolutionAnalysis(Schema):
    criteria: dict[str, Criterion]
    overall_score: int = Field(ge=0, le=100)
    summary: str = Field(max_length=3000)
    key_strengths: list[str]
    key_risks: list[str]
    recommended_improvements: list[str]
    source: str = "mock"

    @model_validator(mode="after")
    def check_formula(self):
        if set(self.criteria) != {
            "creativity",
            "effectiveness",
            "implementation",
            "feasibility",
        }:
            raise ValueError("Exactly four solution criteria required")
        if any(
            c.max_score != 25 for c in self.criteria.values()
        ) or self.overall_score != sum(c.score for c in self.criteria.values()):
            raise ValueError("Invalid solution total")
        return self


class DeadlineAdvice(Schema):
    days: int = Field(ge=1, le=365)
    reason: str
    source: str = "mock"


class ModerationResult(Schema):
    status: Literal["CLEAN", "FLAGGED", "REVIEW_REQUIRED"]
    reasons: list[str]
    source: str = "mock"


class AnonymousSubmissionResponse(Schema):
    id: str
    label: str
    anonymous_number: int
    title: str
    summary: str
    solution_description: str
    implementation_details: str
    status: str
    ai_analysis: SolutionAnalysis | None
    anonymous: Literal[True] = True


class RevealedMember(Schema):
    id: int
    full_name: str
    email: str
    university: str
    github_url: str
    portfolio_url: str


class RevealedSubmissionResponse(Schema):
    id: str
    label: str
    anonymous_number: int
    title: str
    summary: str
    solution_description: str
    implementation_details: str
    status: str
    ai_analysis: SolutionAnalysis | None
    anonymous: Literal[False] = False
    team_id: int
    team_name: str
    members: list[RevealedMember]
    demo_url: str
    repository_url: str
    project_file_name: str
    problem_id: int
    created_at: datetime
    updated_at: datetime
