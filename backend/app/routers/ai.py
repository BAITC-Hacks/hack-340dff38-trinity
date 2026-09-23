from ..core.enums import Role
from fastapi import APIRouter, Depends
from ..core.auth import current_user, require_role
from ..models import User
from ..schemas import InterviewInput, CardDraft
from ..services.ai.problem_analyzer import analyze
from ..services.ai.problem_scorer import score
from ..services.ai.deadline_advisor import recommend

router = APIRouter(prefix="/ai", tags=["AI assistance"])


@router.post("/problem/analyze")
def analyze_problem(request: InterviewInput, user: User = Depends(current_user)):
    require_role(user, Role.COMPANY)
    return analyze(request).model_dump(by_alias=True)


@router.post("/problem/score")
def score_problem(request: CardDraft, user: User = Depends(current_user)):
    require_role(user, Role.COMPANY)
    return score(request).model_dump(by_alias=True)


@router.post("/deadline/recommend")
def deadline(request: CardDraft, user: User = Depends(current_user)):
    require_role(user, Role.COMPANY)
    return recommend(request).model_dump(by_alias=True)
