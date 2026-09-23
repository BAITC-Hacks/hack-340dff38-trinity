from ...schemas import InterviewInput, InterviewResult, CardDraft, Clarification
from .provider import generate

QUESTIONS = [
    ("need", "Что именно нужно изменить и как проблема влияет на бизнес?"),
    (
        "availableData",
        "Какие данные и материалы доступны? Укажите формат, поля и ограничения доступа.",
    ),
    (
        "expectedResult",
        "Какой готовый результат вы ожидаете: прототип, аналитический отчёт или приложение?",
    ),
    (
        "successCriteria",
        "Как вы измерите успех? Укажите метрики и целевые значения, если они известны.",
    ),
    ("users", "Кто будет пользоваться решением и в каком рабочем процессе?"),
    (
        "constraints",
        "Какие есть технические ограничения, сроки, бюджет и требования к данным?",
    ),
    (
        "interactionFormat",
        "Как команда сможет обсуждать задачу с представителем бизнеса?",
    ),
]


def analyze(request: InterviewInput):
    def fallback():
        data = {
            k: v
            for k, v in request.answers.items()
            if k in CardDraft.model_fields
            or k in {f.alias for f in CardDraft.model_fields.values()}
        }
        data.update(title=request.description[:100], context=request.description)
        draft = CardDraft.model_validate(data)
        missing = [key for key, _ in QUESTIONS if not request.answers.get(key)]
        return InterviewResult(
            questions=[Clarification(id=k, question=q) for k, q in QUESTIONS],
            draft=draft,
            missing_fields=missing,
        )

    return generate(
        InterviewResult,
        "Ask at least 3 relevant clarification questions. Map the supplied answers into an editable card. Never invent missing information. Use the field names from draft as question IDs.",
        request.model_dump(by_alias=True),
        fallback,
    )
