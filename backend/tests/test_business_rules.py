import json
import httpx
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError, OperationalError
import pytest
from app.models import Problem, Submission, Student, PointsTransaction, now
from app.core.config import settings
from app.schemas import CardDraft, QualityAnalysis
from app.services.ai.problem_scorer import score
from app.services.ai import provider
from app.seed import seed
from conftest import auth, payload


def test_claude_provider_accepts_valid_tool_result(monkeypatch):
    monkeypatch.setattr(settings(), "ai_mode", "mock")
    card = CardDraft(context="Магазин хочет сократить возвраты товаров.")
    expected = score(card).model_dump(by_alias=True)
    monkeypatch.setattr(settings(), "ai_mode", "claude")
    monkeypatch.setattr(settings(), "anthropic_api_key", "test-only-key")
    requests = []
    real_client = httpx.Client

    def respond(request):
        requests.append(request)
        body = json.loads(request.content)
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"] == "test-only-key"
        assert body["model"] == settings().anthropic_model
        assert body["tool_choice"] == {"type": "tool", "name": "emit_result"}
        assert "overallScore" in body["tools"][0]["input_schema"]["properties"]
        assert json.loads(body["messages"][0]["content"])["context"] == card.context
        return httpx.Response(
            200,
            json={
                "stop_reason": "tool_use",
                "content": [
                    {"type": "tool_use", "name": "emit_result", "input": expected}
                ],
            },
        )

    monkeypatch.setattr(
        provider.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    result = score(card)
    assert len(requests) == 1
    assert result.source == "claude"
    assert result.overall_score == expected["overallScore"]


def get_review(client, company, problem=4):
    r = client.get(f"/api/company/problems/{problem}/submissions", headers=company)
    assert r.status_code == 200, r.text
    return r.json()


def test_quality_formula_and_catalog_visibility(client):
    card = CardDraft(
        **{
            key: "Конкретное описание с доступными фактами. " * 8
            for key in CardDraft.model_fields
            if key not in {"title", "industry"}
        }
    )
    analysis = score(card)
    assert analysis.overall_score == 100
    assert [
        analysis.criteria[k].max_score
        for k in [
            "context",
            "data",
            "result",
            "success",
            "constraints",
            "users",
            "communication",
        ]
    ] == [20, 20, 15, 15, 10, 10, 10]
    catalog = client.get("/api/problems").json()
    scores = [p["qualityScore"] for p in catalog["items"]]
    assert scores == sorted(scores, reverse=True)
    assert min(scores) < 40 and max(scores) >= 90 and len(scores) == 8
    assert all(
        p["industry"] == "Retail"
        for p in client.get("/api/problems?industry=Retail").json()["items"]
    )


def test_invalid_ai_total_rejected():
    a = score(CardDraft()).model_dump()
    a["overall_score"] = 99
    with pytest.raises(ValueError):
        QualityAnalysis.model_validate(a)


def test_exactly_one_winner_and_early_selection(client, company):
    items = get_review(client, company)["items"]
    assert (
        client.post(
            "/api/problems/4/select-winner",
            headers=company,
            json={"submissionId": items[0]["id"]},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/problems/4/select-winner",
            headers=company,
            json={"submissionId": items[1]["id"]},
        ).status_code
        == 409
    )
    winner_items = get_review(client, company)["items"]
    assert sum(s["status"] == "WINNER" for s in winner_items) == 1
    assert all(not s["anonymous"] and "members" in s for s in winner_items)
    early = get_review(client, company, 1)["items"][0]
    assert (
        client.post(
            "/api/problems/1/select-winner",
            headers=company,
            json={"submissionId": early["id"]},
        ).status_code
        == 409
    )
    assert client.get("/api/problems/4").json()["winner"] is None


def test_db_rejects_second_winner(client):
    with client.db_factory() as db:
        submissions = db.scalars(
            select(Submission).where(Submission.problem_id == 4)
        ).all()
        submissions[0].status = "WINNER"
        db.commit()
        submissions[1].status = "WINNER"
        with pytest.raises(IntegrityError):
            db.commit()


def test_deadline_blocks_create_and_edit(client, student, company):
    assert (
        client.post(
            "/api/problems/4/submissions", headers=student, json=payload()
        ).status_code
        == 409
    )
    existing = get_review(client, company, 1)["items"][0]["id"]
    assert (
        client.post("/api/demo/problems/1/expire", headers=company).status_code == 200
    )
    assert (
        client.patch(
            f"/api/submissions/{existing}", headers=student, json=payload()
        ).status_code
        == 409
    )
    assert client.get("/api/problems/1").json()["acceptingSubmissions"] is False
    assert (
        client.patch(
            "/api/problems/1",
            headers=company,
            json={"deadline": (now() + timedelta(days=1)).isoformat()},
        ).status_code
        == 409
    )


def test_anonymous_dto_redacts_content_and_all_bypass_routes(client, company, student):
    s = get_review(client, company, 1)["items"][0]
    identity = "Qadam Makers Айзат Нурлан Назарбаев KBTU SDU University student@example.com https://github.com/demo-student-11 @aizat +7 777 123 45 67"
    body = payload()
    body["title"] = "Проект Айзат Нурлан"
    body["summary"] = identity
    body["solutionDescription"] = identity + " Описание решения и результата работы."
    body["projectFileName"] = "aizat-nurlan.zip"
    assert (
        client.patch(
            f"/api/submissions/{s['id']}", headers=student, json=body
        ).status_code
        == 200
    )
    serialized = client.get(f"/api/submissions/{s['id']}", headers=company).json()
    forbidden_keys = {
        "teamId",
        "teamName",
        "members",
        "senderId",
        "email",
        "university",
        "repositoryUrl",
        "demoUrl",
        "projectFileName",
        "createdAt",
        "updatedAt",
    }
    assert forbidden_keys.isdisjoint(serialized)
    raw = json.dumps(serialized, ensure_ascii=False)
    for secret in [
        "Айзат",
        "Нурлан",
        "Qadam Makers",
        "KBTU",
        "SDU University",
        "student@example.com",
        "github.com",
        "aizat",
        "777",
    ]:
        assert secret not in raw
    assert (
        client.post(
            f"/api/submissions/{s['id']}/messages",
            headers=student,
            json={"text": identity},
        ).status_code
        == 201
    )
    messages = client.get(
        f"/api/submissions/{s['id']}/messages", headers=company
    ).json()
    assert all("senderId" not in m and "sender_id" not in m for m in messages)
    assert "Айзат" not in json.dumps(messages, ensure_ascii=False)
    for path in [
        "/teams",
        "/students/me",
        "/students/me/points",
        "/students/me/submissions",
        "/students/demo-directory",
    ]:
        assert client.get("/api" + path, headers=company).status_code == 403
    assert (
        client.get(
            f"/api/submissions/{s['id']}/messages", headers=auth(client, 14)
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/company/problems/1/submissions", headers=auth(client, 2)
        ).status_code
        == 403
    )


def test_score_split_95_over_3_and_idempotency(client, company, student):
    items = get_review(client, company)["items"]
    winner_id = items[0]["id"]
    assert (
        client.post(
            "/api/problems/4/select-winner",
            headers=company,
            json={"submissionId": winner_id},
        ).status_code
        == 200
    )
    response = client.post(
        "/api/problems/4/winner-score",
        headers=company,
        json={"score": 95, "feedback": "Хорошая реализация"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["pointsPerStudent"] == "31.67"
    retry = client.post(
        "/api/problems/4/winner-score", headers=company, json={"score": 95}
    )
    assert retry.json()["alreadyAwarded"] is True
    assert (
        client.post(
            "/api/problems/4/winner-score", headers=company, json={"score": 94}
        ).status_code
        == 409
    )
    assert (
        client.get("/api/students/me/points", headers=student).json()["totalPoints"]
        == "61.67"
    )
    with client.db_factory() as db:
        transactions = db.scalars(
            select(PointsTransaction).where(PointsTransaction.problem_id == 4)
        ).all()
        assert len(transactions) == 3
        assert all(t.points == Decimal("31.67") for t in transactions)
        assert db.get(Student, 14).total_points == Decimal("0.00")
        assert db.get(Student, 16).total_points == Decimal("0.00")
    public = client.get("/api/problems/4").json()
    assert public["winner"]["id"] == winner_id
    assert "submissions" not in public
    for loser in items[1:]:
        assert loser["id"] not in json.dumps(public)
        assert client.get(f"/api/submissions/{loser['id']}").status_code == 401


@pytest.mark.parametrize("score_value", [-1, 101, 1.5, True, "95"])
def test_score_validation(client, company, score_value):
    assert (
        client.post(
            "/api/problems/4/winner-score", headers=company, json={"score": score_value}
        ).status_code
        == 422
    )


def test_zero_score_counts_as_completed(client, company):
    item = get_review(client, company)["items"][0]
    client.post(
        "/api/problems/4/select-winner",
        headers=company,
        json={"submissionId": item["id"]},
    )
    assert (
        client.post(
            "/api/problems/4/winner-score", headers=company, json={"score": 0}
        ).status_code
        == 200
    )
    assert client.get("/api/problems/4").json()["completed"] is True
    assert (
        client.post(
            "/api/problems/4/winner-score", headers=company, json={"score": 0}
        ).json()["alreadyAwarded"]
        is True
    )


def test_invalid_json_and_unavailable_claude_fallback(client, company, monkeypatch):
    monkeypatch.setattr(settings(), "ai_mode", "claude")
    monkeypatch.setattr(settings(), "anthropic_api_key", "test-only-key")
    attempts = []

    def bad(*args):
        attempts.append(1)
        return "{not-json"

    monkeypatch.setattr(provider, "request_claude", bad)
    result = client.post(
        "/api/ai/problem/analyze",
        headers=company,
        json={"description": "Нужно уменьшить возвраты товаров в нашем магазине."},
    )
    assert result.status_code == 200 and len(result.json()["questions"]) >= 3
    assert result.json()["source"] == "mock_fallback" and len(attempts) == 2
    monkeypatch.setattr(settings(), "anthropic_api_key", "")
    assert (
        client.post("/api/ai/problem/score", headers=company, json={}).json()["source"]
        == "mock_fallback"
    )


def test_foreign_company_cannot_mutate_or_see_reviews(client, company):
    other = auth(client, 2)
    for path, method, body in [
        ("/problems/1", "PATCH", {"title": "Чужое изменение"}),
        ("/problems/1/publish", "POST", {}),
        ("/demo/problems/1/expire", "POST", {}),
        ("/problems/4/winner-score", "POST", {"score": 90}),
    ]:
        assert (
            client.request(method, "/api" + path, headers=other, json=body).status_code
            == 403
        )
    assert (
        client.post(
            "/api/ai/problem/analyze",
            headers=auth(client, 11),
            json={"description": "Текст для проверки доступа"},
        ).status_code
        == 403
    )
    assert client.get("/api/admin/moderation", headers=company).status_code == 403


def test_demo_full_lifecycle_without_database_edits(client, company, student):
    interview = client.post(
        "/api/ai/problem/analyze",
        headers=company,
        json={"description": "Магазин хочет сократить возвраты интернет-заказов."},
    ).json()
    assert len(interview["questions"]) >= 3
    assert interview["draft"]["availableData"] == ""
    draft = interview["draft"]
    draft.update(
        industry="Custom industry", deadline=(now() + timedelta(days=7)).isoformat()
    )
    response = client.post("/api/problems", headers=company, json=draft)
    assert response.status_code == 201, response.text
    pid = response.json()["id"]
    assert client.get(f"/api/problems/{pid}").status_code == 404
    assert (
        client.post(f"/api/problems/{pid}/publish", headers=company).status_code == 200
    )
    assert "Custom industry" in client.get("/api/problems").json()["industries"]
    team = client.post(
        "/api/teams", headers=student, json={"name": "Новая соло-команда"}
    ).json()
    assert len(team["members"]) == 1
    sub = client.post(
        f"/api/problems/{pid}/submissions", headers=student, json=payload(team["id"])
    )
    assert sub.status_code == 201, sub.text
    assert (
        client.post(
            f"/api/problems/{pid}/submissions",
            headers=student,
            json=payload(team["id"]),
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/teams/{team['id']}/members", headers=student, json={"studentId": 12}
        ).status_code
        == 409
    )
    q = client.post(
        f"/api/problems/{pid}/questions",
        headers=student,
        json={"text": "Какие поля есть в CSV?"},
    ).json()
    assert (
        client.post(
            f"/api/questions/{q['id']}/answers",
            headers=company,
            json={"text": "SKU, размер и причина возврата."},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/problems/{pid}/comments",
            headers=student,
            json={"text": "Пока рано."},
        ).status_code
        == 409
    )
    edit = client.patch(
        f"/api/problems/{pid}",
        headers=company,
        json={
            "availableData": "CSV: SKU, размер, дата заказа и причина возврата. 12 месяцев истории."
        },
    )
    assert edit.status_code == 200 and edit.json()["revisions"][0]["changedFields"] == [
        "available_data"
    ]
    client.post(f"/api/demo/problems/{pid}/expire", headers=company)
    client.post(
        f"/api/problems/{pid}/select-winner",
        headers=company,
        json={"submissionId": sub.json()["id"]},
    )
    result = client.post(
        f"/api/problems/{pid}/winner-score", headers=company, json={"score": 87}
    )
    assert result.status_code == 200 and result.json()["pointsPerStudent"] == "87.00"
    assert (
        client.post(
            f"/api/problems/{pid}/comments",
            headers=student,
            json={"text": "Предлагаю добавить сегментацию."},
        ).status_code
        == 201
    )


def test_moderation_hides_and_restores_public_content(client):
    admin = auth(client, 99)
    queue = client.get("/api/admin/moderation", headers=admin).json()
    item = next(
        i
        for i in queue["items"]
        if i["entityType"] == "problem" and i["entityId"] == "1"
    )
    assert (
        client.post(
            f"/api/admin/moderation/{item['id']}/hide", headers=admin
        ).status_code
        == 200
    )
    assert client.get("/api/problems/1").status_code == 404
    assert 1 not in [p["id"] for p in client.get("/api/problems").json()["items"]]
    assert (
        client.post(
            f"/api/admin/moderation/{item['id']}/approve", headers=admin
        ).status_code
        == 200
    )
    assert client.get("/api/problems/1").status_code == 200


def test_seed_idempotent(client):
    with client.db_factory() as db:
        assert seed(db) is False
        assert db.scalar(select(func.count()).select_from(Submission)) == 12


def test_demo_tools_can_be_disabled(client, company, monkeypatch):
    monkeypatch.setattr(settings(), "demo_tools_enabled", False)
    assert (
        client.post("/api/demo/problems/1/expire", headers=company).status_code == 404
    )


def test_db_error_does_not_expose_trace_or_sql(client, monkeypatch):
    from sqlalchemy.orm import Session

    def fail(*args, **kwargs):
        raise OperationalError("SECRET SQL", {}, Exception("internal server detail"))

    monkeypatch.setattr(Session, "execute", fail)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert "SECRET" not in response.text and "Traceback" not in response.text


def test_all_dashboard_data_endpoints(client, company, student):
    for route in ["/company/me", "/company/problems", "/auth/me"]:
        response = client.get("/api" + route, headers=company)
        assert response.status_code == 200, response.text
    for route in [
        "/students/me",
        "/students/me/points",
        "/students/me/submissions",
        "/students/demo-directory",
        "/teams",
    ]:
        response = client.get("/api" + route, headers=student)
        assert response.status_code == 200, response.text


def test_privacy_redaction_preserves_unrelated_words():
    from app.services.privacy import scrub

    assert (
        scrub("Прототип работает с синтетическими данными.", ["Ким"])
        == "Прототип работает с синтетическими данными."
    )
    assert "Ким" not in scrub("Автор: Аружан Ким.", ["Ким"])
    assert "github.com" not in scrub("Код: github.com/student/repo", [])


def test_public_questions_cannot_link_known_author_to_anonymous_solution(
    client, student
):
    assert (
        client.post(
            "/api/problems/1/questions",
            headers=student,
            json={"text": "Я Айзат Нурлан, наш Solution #1 использует CSV."},
        ).status_code
        == 201
    )
    question = client.get("/api/problems/1").json()["questions"][-1]
    assert "Айзат" not in question["text"] and "Нурлан" not in question["text"]
