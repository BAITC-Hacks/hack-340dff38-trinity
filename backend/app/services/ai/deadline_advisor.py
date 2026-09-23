from ...schemas import CardDraft, DeadlineAdvice
from .provider import generate


def recommend(card: CardDraft):
    def fallback():
        combined = (card.expected_result + card.constraints).lower()
        days = (
            21
            if any(w in combined for w in ["интеграц", "integration", "мобильн"])
            else 14
        )
        return DeadlineAdvice(
            days=days,
            reason="Ориентировочно: изучение данных, разработка прототипа и проверка результата. Итоговый срок выбирает компания.",
        )

    return generate(
        DeadlineAdvice,
        "Recommend a realistic number of calendar days based on scope, complexity, expected deliverables and constraints. This is advisory only.",
        card.model_dump(by_alias=True),
        fallback,
    )
