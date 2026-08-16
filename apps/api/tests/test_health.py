from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-interkorean-dialogue-api",
    }


def test_phase_two_health_routes_without_external_calls() -> None:
    for path in ("/health/db", "/health/openrouter", "/health/public-data", "/health/all"):
        response = client.get(path)
        assert response.status_code == 200
        assert "status" in response.json()
