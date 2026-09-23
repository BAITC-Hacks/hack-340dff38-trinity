from ...schemas import Criterion, SolutionAnalysis
from .provider import generate


def evaluate(problem, submission):
    def fallback():
        description = submission.get("solutionDescription", "")
        implementation = submission.get("implementationDetails", "")
        scores = {
            "creativity": min(21, 9 + len(description) // 70),
            "effectiveness": min(23, 10 + len(description) // 55),
            "implementation": min(22, 8 + len(implementation) // 55),
            "feasibility": min(22, 10 + len(implementation) // 75),
        }
        criteria = {
            k: Criterion(
                score=v,
                max_score=25,
                reasoning="Детерминированная демо-оценка по описанию. Код и внешние ссылки не проверены.",
                strengths=["Предоставлено описание подхода и реализации."],
                weaknesses=["Нет независимой проверки работоспособности и метрик."],
                recommendations=[
                    "Проведите демонстрацию и приложите результаты тестирования."
                ],
            )
            for k, v in scores.items()
        }
        return SolutionAnalysis(
            criteria=criteria,
            overall_score=sum(scores.values()),
            summary="Предварительный разбор представленных материалов. Проверьте решение на данных бизнеса и сопоставьте результат с критериями успеха.",
            key_strengths=[
                "Подход и реализация описаны в заявке.",
                "Материалы готовы к обсуждению с бизнесом.",
            ],
            key_risks=[
                "Работа кода не подтверждена автоматической проверкой.",
                "Результат на реальных данных ещё нужно проверить.",
            ],
            recommended_improvements=[
                "Покажите сценарий от входных данных до результата.",
                "Добавьте измерения качества и описание ограничений.",
            ],
        )

    return generate(
        SolutionAnalysis,
        "Evaluate solution against the business problem, with creativity, effectiveness, implementation, feasibility each out of 25. Only evaluate supplied text. Do not claim to have visited links or executed code. Include evidence, strengths, risks and improvements. Do not recommend/select a winner.",
        {"problem": problem, "submission": submission},
        fallback,
    )
