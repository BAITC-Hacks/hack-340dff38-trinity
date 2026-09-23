from ...schemas import CardDraft, Criterion, QualityAnalysis, QUALITY_WEIGHTS
from .provider import generate

FIELDS = {
    "context": ("context", "need"),
    "data": ("available_data",),
    "result": ("expected_result",),
    "success": ("success_criteria",),
    "constraints": ("constraints",),
    "users": ("users",),
    "communication": ("business_contact", "interaction_format"),
}
TIPS = {
    "context": "Опишите текущий процесс, проблему и её влияние на бизнес.",
    "data": "Укажите источники, формат, поля данных и способ доступа.",
    "result": "Перечислите конкретные материалы, которые должна сдать команда.",
    "success": "Добавьте измеримые метрики и целевые значения.",
    "constraints": "Уточните сроки, технологии, ресурсы и ограничения доступа.",
    "users": "Назовите пользователей и сценарии использования.",
    "communication": "Укажите контакт и формат встреч или обратной связи.",
}


def score(card: CardDraft):
    def fallback():
        criteria = {}
        for key, maximum in QUALITY_WEIGHTS.items():
            values = [getattr(card, f) for f in FIELDS[key]]
            coverage = sum(min(len(v.strip()) / 110, 1) for v in values) / len(values)
            points = round(maximum * coverage)
            criteria[key] = Criterion(
                score=points,
                max_score=maximum,
                reasoning=(
                    "Демо-оценка полноты: раздел заполнен подробно."
                    if points == maximum
                    else "Демо-оценка полноты: описанию не хватает конкретики."
                ),
                missing=[] if points == maximum else [TIPS[key]],
                recommendations=[] if points == maximum else [TIPS[key]],
            )
        return QualityAnalysis(
            criteria=criteria, overall_score=sum(c.score for c in criteria.values())
        )

    return generate(
        QualityAnalysis,
        "Score task specification quality. Exact maxima: context 20, data 20, result 15, success 15, constraints 10, users 10, communication 10. Sum must equal overallScore. Explain missing evidence and improvements. Length alone is not quality.",
        card.model_dump(by_alias=True),
        fallback,
    )
