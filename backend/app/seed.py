"""Idempotent synthetic demo data; all dates are relative to the seed date."""

from .core.enums import Role, ProblemStatus
from datetime import timedelta
from sqlalchemy import select, text
from .core.config import settings
from .core.database import SessionLocal
from .core.auth import utc
from .models import (
    User,
    Company,
    Student,
    Team,
    TeamMember,
    Problem,
    Submission,
    SubmissionMember,
    SubmissionChat,
    SubmissionReview,
    Question,
    Answer,
    Comment,
    Message,
    now,
)
from .schemas import WinnerScoreInput
from .services.problems import update_quality, card_from_problem
from .services.ai.solution_evaluator import evaluate
from .services.moderation import record_moderation
from .services.submissions import select_winner, award_score

COMPANIES = [
    ("Qadam Retail", "Retail", "Алматы", "Омниканальный магазин одежды и аксессуаров."),
    ("Nomad Pay", "FinTech", "Астана", "Платёжные решения для малого бизнеса."),
    (
        "Jasyl Agro",
        "Agriculture",
        "Кызылорда",
        "Цифровые инструменты для фермерских хозяйств.",
    ),
    ("Bilim Lab", "Education", "Алматы", "Образовательная платформа для колледжей."),
    (
        "Steppe Logistics",
        "Logistics",
        "Шымкент",
        "Региональная доставка для локальных компаний.",
    ),
    (
        "Orda Factory",
        "Manufacturing",
        "Караганда",
        "Производство деталей и управление качеством.",
    ),
]
STUDENTS = [
    "Айзат Нурлан",
    "Данияр Ахметов",
    "Алина Садыкова",
    "Тимур Оспанов",
    "Аружан Ким",
    "Мирас Алиев",
    "Диана Ермек",
    "Аслан Жумабаев",
    "София Бек",
    "Ерасыл Серик",
]
SPECS = [
    (
        1,
        "Меньше возвратов, больше довольных покупателей",
        "Retail",
        14,
        "В интернет-магазине одежды 18% заказов возвращаются. Менеджеры вручную разбирают причины, а покупателям сложно выбрать размер.",
        "Снизить возвраты из-за неподходящего размера и дать команде магазина понятную аналитику причин без изменения текущей CRM.",
        "Обезличенный CSV за 12 месяцев: SKU, размер, категория, дата покупки, факт возврата и причина. 24 000 строк; доступ после первого обсуждения.",
        "Веб-прототип рекомендаций по размеру, дашборд причин возвратов, инструкция по запуску и отчёт с проверкой на отложенной выборке.",
        "Сравнить с базовым подбором по таблице размеров; целевой рост точности не менее 10%. Проверить 20 типовых сценариев и описать ошибки.",
    ),
    (
        2,
        "Понятный денежный поток для малого бизнеса",
        "FinTech",
        21,
        "Владельцы небольших кафе сверяют поступления и расходы в разных таблицах. Планирование закупок занимает несколько часов каждую неделю.",
        "Объединить финансовые потоки в одном обзоре и заранее показывать дни с возможным дефицитом средств, с объяснением причин прогноза.",
        "Синтетический CSV: transaction_id, date, amount, category, merchant_id; 50 000 записей за год. Описание полей и тестовый набор доступны по email.",
        "Запускаемый локально дашборд поступлений, расходов и прогноза на 14 дней с фильтрами, тестами, README и воспроизводимой демонстрацией.",
        "Ошибка прогноза на отложенном месяце ниже наивного среднего; импорт 50 000 строк до 10 секунд; 5 сценариев проверены с владельцами.",
    ),
    (
        3,
        "Когда поливать: помощник для фермерского хозяйства",
        "Agriculture",
        18,
        "Фермеры ведут записи влажности почвы в таблицах. Полив назначается по календарю и не всегда соответствует фактическому состоянию поля.",
        "Помочь агроному принимать решение о поливе на основе доступных измерений.",
        "CSV с датой, участком, влажностью и объёмом полива за один сезон. Пропуски и единицы измерения отмечены в описании.",
        "Прототип рекомендаций с объяснениями и визуализацией истории влажности.",
        "Проверить рекомендации на исторических данных и описать ограничения.",
    ),
    (
        1,
        "Умный прогноз остатков для локальных магазинов",
        "Retail",
        -2,
        "В трёх магазинах популярные позиции заканчиваются раньше поставки, а часть ассортимента остаётся на складе. Планирование ведётся вручную.",
        "Дать закупщику рекомендации по пополнению запасов с учётом сезонности, сроков поставки и наблюдаемого спроса по каждой категории.",
        "CSV продаж за 18 месяцев: date, store_id, sku, units_sold, stock, price. Каталог из 500 SKU и сроки поставок; персональных данных нет.",
        "Прототип прогноза спроса с импортом CSV, объяснением рекомендации закупки, дашбордом остатков, автотестами и инструкцией запуска.",
        "Сравнение с сезонным средним на последних 8 неделях; улучшение WAPE не менее 10%; ручная проверка 10 рекомендаций закупщиком.",
    ),
    (
        4,
        "Ранние сигналы: кому нужна помощь в обучении",
        "Education",
        0.3,
        "Кураторы замечают трудности студентов только к концу семестра. Данные посещаемости и заданий находятся в разных файлах.",
        "Помочь кураторам вовремя предлагать поддержку студентам.",
        "Обезличенные учебные записи: посещения, задания и даты. 1 200 синтетических профилей.",
        "Дашборд для куратора с объяснимыми сигналами и списком рекомендуемых действий.",
        "Уменьшить время ручного анализа и проверить понятность сигналов с 3 кураторами.",
    ),
    (
        5,
        "Хочется улучшить доставку",
        "Logistics",
        10,
        "Доставка часто опаздывает.",
        "Нужна автоматизация.",
        "Есть таблицы.",
        "Удобный сервис.",
        "Чтобы было быстрее.",
    ),
    (
        6,
        "Дефекты под контролем: аналитика производства",
        "Manufacturing",
        25,
        "Контролёры записывают дефекты партий вручную. Руководителю сложно увидеть повторяющиеся причины брака между сменами.",
        "Сократить ручное сведение отчётов и показать причины дефектов.",
        "CSV за 6 месяцев: партия, линия, смена, тип дефекта, количество. Фотографии не предоставляются.",
        "Дашборд контроля качества с диаграммой причин, фильтрами и экспортом отчёта.",
        "Сведение месячного отчёта до 5 минут и корректность на 30 контрольных примерах.",
    ),
    (
        1,
        "Обратная связь, которую слышит бизнес",
        "Retail",
        -10,
        "Отзывы покупателей из нескольких каналов обрабатываются вручную. Повторяющиеся проблемы теряются в большом количестве сообщений.",
        "Объединить темы обращений и помочь менеджерам выбирать улучшения на основе частоты и влияния проблемы.",
        "3 000 синтетических отзывов в CSV: дата, канал, текст, категория. Персональные данные удалены.",
        "Рабочий прототип классификации тем с дашбордом и проверкой на размеченной выборке.",
        "Macro F1 не ниже 0.75 на тестовой выборке; каждую категорию можно проверить по примерам.",
    ),
]


def seed(db):
    if db.scalar(select(User.id).limit(1)):
        return False
    for i, (name, industry, city, description) in enumerate(COMPANIES, 1):
        email = "company@example.com" if i == 1 else f"company{i}@example.com"
        db.add(User(id=i, role=Role.COMPANY, email=email))
        db.flush()
        db.add(
            Company(
                id=i,
                user_id=i,
                name=name,
                industry=industry,
                city=city,
                description=description,
                email=email,
                telegram=f"sana_demo_company{i}",
            )
        )
    for i, name in enumerate(STUDENTS, 11):
        db.add(
            User(
                id=i,
                role=Role.STUDENT,
                email="student@example.com" if i == 11 else f"student{i}@example.com",
            )
        )
        db.flush()
        db.add(
            Student(
                id=i,
                full_name=name,
                university=["KBTU", "Nazarbayev University", "SDU University"][i % 3],
                specialization="Software Engineering",
                course=i % 4 + 1,
                skills=(
                    ["Python", "React", "SQL"]
                    if i % 2
                    else ["Figma", "Data analysis", "TypeScript"]
                ),
                interests=["AI", "Продуктовая разработка"],
                github_url=f"https://github.com/demo-student-{i}",
                portfolio_url="",
            )
        )
    db.add(User(id=99, role=Role.ADMIN, email="admin@example.com"))
    db.flush()
    rosters = [[11, 12, 13], [14, 15], [16], [17, 18], [19, 20]]
    for i, members in enumerate(rosters, 1):
        db.add(
            Team(
                id=i,
                name=[
                    "Qadam Makers",
                    "Nomad Builders",
                    "Solo / Miras",
                    "Data Garden",
                    "Orda Engineers",
                ][i - 1],
            )
        )
        db.flush()
        for j, student in enumerate(members):
            db.add(
                TeamMember(
                    team_id=i, student_id=student, role="OWNER" if j == 0 else "MEMBER"
                )
            )
    db.flush()
    for i, spec in enumerate(SPECS, 1):
        company_id, title, industry, days, context, need, data, result, success = spec
        p = Problem(
            id=i,
            company_id=company_id,
            title=title,
            industry=industry,
            context=context,
            need=need,
            available_data=data,
            expected_result=result,
            success_criteria=success,
            users="Менеджеры и операционные специалисты компании. Решение используется в ежедневной работе: загрузка данных, анализ результатов и принятие решений.",
            constraints="Прототип должен запускаться локально, использовать обезличенные данные и открытые библиотеки. Документируйте ограничения, не передавайте данные третьим лицам.",
            business_contact="Связь с владельцем задачи через email компании на странице. Доступ к демо-данным и ответы на уточнения предоставляются в течение двух рабочих дней.",
            interaction_format="Две встречи по 30 минут: уточнение задачи и демонстрация результата. Между встречами — публичные вопросы и обсуждение решения внутри платформы.",
            deadline=now() + timedelta(days=days),
            status=ProblemStatus.PUBLISHED,
            published_at=now() - timedelta(days=5),
        )
        if i == 6:
            p.users = p.constraints = p.interaction_format = p.business_contact = ""
        db.add(p)
        db.flush()
        update_quality(db, p)
        record_moderation(db, "problem", p.id, p.title + " " + p.context)
    db.flush()
    mapping = [
        (1, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 1),
        (4, 2),
        (4, 3),
        (5, 4),
        (6, 5),
        (7, 2),
        (8, 1),
        (8, 5),
    ]
    counters = {}
    for j, (pid, tid) in enumerate(mapping):
        counters[pid] = counters.get(pid, 0) + 1
        p = db.get(Problem, pid)
        description = (
            "Решение объединяет загрузку CSV, проверку качества данных и понятный дашборд для специалиста. Пользователь выбирает период, видит ключевые показатели и получает объяснение каждого результата. "
            "Добавлены сравнение с базовым подходом, фильтры по сегментам и экспорт отчёта. Для демонстрации подготовлены синтетические данные и сценарии с пропусками. "
            "Все вычисления воспроизводимы; ограничения модели указаны в интерфейсе. Подход можно проверить без подключения внешних сервисов."
        ) * (2 if j % 2 == 0 else 1)
        implementation = (
            "Backend: Python и FastAPI; frontend: React и TypeScript; хранение: PostgreSQL. Данные валидируются при импорте, ошибки показываются с номером строки. "
            "Реализованы тесты преобразований, обработка отсутствующих значений, независимая тестовая выборка и сравнение метрик с базовым алгоритмом. "
            "Запуск через Docker Compose, README содержит команды и ограничения. Среднее время обработки 10 000 строк на демо-наборе измерено локально; на реальной инфраструктуре требуется повторная проверка."
        ) * (2 if j % 3 == 0 else 1)
        s = Submission(
            problem_id=pid,
            team_id=tid,
            title=[
                "Прототип с объяснимой аналитикой",
                "Рабочий инструмент на каждый день",
                "От данных к решению",
            ][j % 3],
            summary="Готовый веб-прототип: импорт данных, аналитика, объяснения и проверка качества. Материалы для запуска и демонстрации приложены.",
            solution_description=description,
            implementation_details=implementation,
            demo_url="https://example.com/demo",
            repository_url="https://example.com/repository",
            project_file_name="project-demo.zip",
            anonymous_number=counters[pid],
            created_at=min(
                now() - timedelta(days=3), utc(p.deadline) - timedelta(hours=1)
            ),
        )
        db.add(s)
        db.flush()
        for student_id in rosters[tid - 1]:
            db.add(SubmissionMember(submission_id=s.id, student_id=student_id))
        chat = SubmissionChat(submission_id=s.id)
        db.add(chat)
        db.flush()
        db.add(
            Message(
                chat_id=chat.id,
                sender_type=Role.COMPANY,
                sender_id=p.company_id,
                text="Подскажите, как решение обрабатывает отсутствующие значения в исходных данных?",
            )
        )
        db.add(
            Message(
                chat_id=chat.id,
                sender_type=Role.STUDENT,
                sender_id=rosters[tid - 1][0],
                text="Показываем долю пропусков, исключаем критически неполные записи и отмечаем ограничения в отчёте.",
            )
        )
        analysis = evaluate(
            card_from_problem(p).model_dump(by_alias=True),
            {
                "solutionDescription": description,
                "implementationDetails": implementation,
            },
        )
        db.add(
            SubmissionReview(
                submission_id=s.id, analysis=analysis.model_dump(by_alias=True)
            )
        )
        record_moderation(db, "submission", s.id, s.summary)
    q = Question(
        problem_id=1,
        author_id=11,
        text="Будет ли доступен справочник размеров для разных брендов?",
    )
    db.add(q)
    db.flush()
    db.add(
        Answer(
            question_id=q.id,
            author_id=1,
            text="Да, подготовим CSV с таблицами размеров для 12 основных брендов.",
        )
    )
    db.commit()
    winner = db.scalar(
        select(Submission).where(Submission.problem_id == 8, Submission.team_id == 1)
    )
    owner = db.get(User, 1)
    select_winner(db, owner, 8, winner.id)
    award_score(
        db,
        owner,
        8,
        WinnerScoreInput(
            score=90,
            feedback="Понятная аналитика, воспроизводимая демонстрация и хорошо описанные ограничения.",
        ),
    )
    db.add(
        Comment(
            problem_id=8,
            author_id=14,
            text="Полезно добавить сравнение тем отзывов по месяцам — так можно проверить эффект изменений.",
        )
    )
    flagged = Comment(
        problem_id=8,
        author_id=15,
        text="Тест модерации: spam — free money. Синтетический пример нежелательного комментария.",
    )
    db.add(flagged)
    db.flush()
    record_moderation(db, "comment", flagged.id, flagged.text)
    if db.get_bind().dialect.name == "postgresql":
        # Explicit seed IDs do not advance PostgreSQL sequences automatically.
        for table in ("users", "companies", "teams", "problems"):
            db.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT MAX(id) FROM {table}), true)"
                )
            )
    db.commit()
    return True


def main():
    cfg = settings()
    mode = cfg.ai_mode
    cfg.ai_mode = "mock"
    try:
        with SessionLocal() as db:
            print(
                "Seed created: 6 companies, 10 students, 5 teams, 8 problems, 12 submissions."
                if seed(db)
                else "Seed already exists; no changes made."
            )
    finally:
        cfg.ai_mode = mode


if __name__ == "__main__":
    main()
