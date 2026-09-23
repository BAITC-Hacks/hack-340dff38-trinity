import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app
from app.seed import seed


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings().ai_mode = "mock"
    with factory() as db:
        seed(db)

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        client.db_factory = factory
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def auth(client, user=1):
    response = client.post("/api/auth/demo-login", json={"userId": user})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture
def company(client):
    return auth(client, 1)


@pytest.fixture
def student(client):
    return auth(client, 11)


def payload(team_id=1):
    return {
        "teamId": team_id,
        "title": "Рабочий проект",
        "summary": "Прототип с импортом данных и понятной аналитикой.",
        "solutionDescription": "Пользователь загружает CSV, получает объяснимый прогноз и сравнение с базовым методом. "
        * 4,
        "implementationDetails": "FastAPI, React, PostgreSQL; есть тесты импорта, обработка пропусков и инструкция запуска. "
        * 4,
        "demoUrl": "https://example.com/demo",
        "repositoryUrl": "https://example.com/repo",
        "projectFileName": "solution.zip",
    }
