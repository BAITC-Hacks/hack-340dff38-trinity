"""Exercise a running, disposable demo; creates a task, team, submission and points.

Usage: python scripts/smoke_demo.py http://127.0.0.1:8080
Use only on a synthetic test environment with demo auth and demo tools enabled.
No external packages or paid AI calls are needed.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

base_url = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8080"
opener = build_opener(ProxyHandler({}))


def call(method, path, data=None, token=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        base_url + "/api" + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers,
        method=method,
    )
    try:
        response = opener.open(request, timeout=45)
    except HTTPError as error:
        response = error
    with response:
        body = response.read().decode()
        assert response.code == expected, f"{method} {path}: {response.code}: {body}"
        return json.loads(body)


with opener.open(base_url + "/", timeout=20) as page:
    assert page.status == 200 and '<div id="root">' in page.read().decode()
assert call("GET", "/health")["aiMode"] == "mock"
company = call("POST", "/auth/demo-login", {"userId": 1})["token"]
students = {
    uid: call("POST", "/auth/demo-login", {"userId": uid})["token"]
    for uid in (11, 12, 13)
}
before = {
    uid: Decimal(call("GET", "/students/me", token=token)["totalPoints"])
    for uid, token in students.items()
}
interview = call(
    "POST",
    "/ai/problem/analyze",
    {"description": "Магазину нужен анализ причин возврата товаров."},
    company,
)
assert interview["source"] == "mock" and len(interview["questions"]) >= 3
draft = interview["draft"]
draft.update(
    title="CI: анализ возвратов",
    industry="Retail",
    deadline=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
)
problem_id = call("POST", "/problems", draft, company, 201)["id"]
call("POST", f"/problems/{problem_id}/publish", token=company)
team = call(
    "POST", "/teams", {"name": "CI Demo Team", "memberIds": [12, 13]}, students[11], 201
)
submission = call(
    "POST",
    f"/problems/{problem_id}/submissions",
    {
        "teamId": team["id"],
        "title": "Аналитика возвратов",
        "summary": "Прототип для анализа синтетических CSV-данных.",
        "solutionDescription": "Загрузка CSV, поиск повторяющихся причин возврата и объяснимый отчёт для менеджера. "
        * 3,
        "implementationDetails": "React, FastAPI, PostgreSQL. Валидация CSV и тесты расчётов. "
        * 3,
        "repositoryUrl": "https://example.com/ci-project",
    },
    students[11],
    201,
)
reviews = call("GET", f"/company/problems/{problem_id}/submissions", token=company)[
    "items"
]
anonymous = json.dumps(reviews, ensure_ascii=False)
for forbidden in (
    '"teamId"',
    '"members"',
    '"email"',
    '"repositoryUrl"',
    "CI Demo Team",
    "example.com/ci-project",
):
    assert forbidden not in anonymous, f"Identity leak: {forbidden}"
winner = {"submissionId": submission["id"]}
call("POST", f"/problems/{problem_id}/select-winner", winner, company, 409)
call("POST", f"/demo/problems/{problem_id}/expire", token=company)
call("POST", f"/problems/{problem_id}/select-winner", winner, company)
award = call("POST", f"/problems/{problem_id}/winner-score", {"score": 95}, company)
assert award["pointsPerStudent"] == "31.67"
assert (
    call("POST", f"/problems/{problem_id}/winner-score", {"score": 95}, company)[
        "alreadyAwarded"
    ]
    is True
)
for uid, token in students.items():
    ledger = call("GET", "/students/me/points", token=token)
    assert Decimal(ledger["totalPoints"]) - before[uid] == Decimal("31.67")
    assert sum(item["problemId"] == problem_id for item in ledger["transactions"]) == 1
print(
    "PASS: frontend, proxy, interview, submission, anonymity, deadline, winner, 95/3 and idempotency"
)
