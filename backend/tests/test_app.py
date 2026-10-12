"""Smoke tests for app-level routes not covered by the API tests."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_route():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_docs_route():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_previous_docs_url_redirects():
    response = client.get("/api/docs", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_plain_postgresql_url_gets_async_driver():
    from app.database.session import normalize_async_database_url

    normalized = normalize_async_database_url(
        "postgresql://lenny:local-password@127.0.0.1:5432/lenny_assistant"
    )
    assert normalized.startswith("postgresql+asyncpg://")
