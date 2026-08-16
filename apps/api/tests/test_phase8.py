import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.simulation.schemas import SimulationCreate


def test_user_mode_schema() -> None:
    request = SimulationCreate(scenario="separated_families", mode="USER_SOUTH_VS_AI_NORTH")
    assert request.mode == "USER_SOUTH_VS_AI_NORTH"


def test_user_turn_endpoint(monkeypatch) -> None:
    async def fake_user_turn(session_id, request):
        return {"state": {"status": "RUNNING"}, "turn": {"message": "답변"}, "user_turn": {"message": request.message}}

    monkeypatch.setattr("app.main.user_turn", fake_user_turn)
    response = TestClient(app).post("/api/v1/simulations/test/user-turn", json={"message": "실무협의를 제안합니다."})
    assert response.status_code == 200
    assert response.json()["user_turn"]["message"] == "실무협의를 제안합니다."


def test_suggestions_endpoint(monkeypatch) -> None:
    monkeypatch.setattr("app.main.suggestions", lambda session_id: ["제안 1", "제안 2"])
    response = TestClient(app).post("/api/v1/simulations/test/suggestions")
    assert response.status_code == 200
    assert len(response.json()["suggestions"]) == 2


def test_stream_endpoint_emits_events(monkeypatch) -> None:
    from app.simulation.schemas import SimulationState

    monkeypatch.setattr("app.main.get_simulation", lambda session_id: SimulationState(session_id=session_id, scenario_id="separated_families"))
    async def fake_next(session_id):
        return {"state": {"status": "RUNNING"}, "turn": {"speaker_agent_id": "north_chief", "message": "응답"}, "result": None}

    monkeypatch.setattr("app.main.next_turn", fake_next)
    response = TestClient(app).post("/api/v1/simulations/test/next/stream")
    assert response.status_code == 200
    assert "event: token" in response.text
    assert "event: done" in response.text
