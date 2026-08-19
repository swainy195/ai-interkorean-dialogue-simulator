import os
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json

from app.connectivity import check_openrouter, check_public_data, check_supabase
from app.agents.schemas import AgentRequest
from app.agents.service import respond
from app.simulation.schemas import SimulationCreate, UserTurnRequest
from app.simulation.service import create as create_simulation, get as get_simulation, get_evidence as get_simulation_evidence, get_result as get_simulation_result, next_speaker, next_turn, suggestions, user_turn


logger = logging.getLogger(__name__)


def allowed_origins() -> list[str]:
    configured = os.getenv("WEB_BASE_URL", "http://localhost:5173")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(title="AI Inter-Korean Dialogue API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_checks: dict[str, dict[str, Any]] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-interkorean-dialogue-api"}


async def _cached(name: str, checker: Any) -> dict[str, Any]:
    if name not in _checks:
        _checks[name] = await checker()
    return _checks[name]


@app.get("/health/db")
async def health_db() -> dict[str, Any]:
    return await _cached("db", check_supabase)


@app.get("/health/openrouter")
async def health_openrouter() -> dict[str, Any]:
    return await _cached("openrouter", check_openrouter)


@app.get("/health/public-data")
async def health_public_data() -> dict[str, Any]:
    return await _cached("public-data", check_public_data)


@app.get("/health/all")
async def health_all() -> dict[str, Any]:
    checks = {name: value for name, value in _checks.items()}
    ok = all(value.get("status") == "ok" for value in checks.values()) if checks else False
    return {"status": "ok" if ok else "degraded", "service": "ai-interkorean-dialogue-api", "checks": checks}


@app.post("/api/v1/agents/respond")
async def agent_respond(request: AgentRequest) -> dict[str, Any]:
    try:
        return await respond(request)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/simulations")
def simulation_create(request: SimulationCreate) -> dict[str, Any]:
    try:
        state = create_simulation(request)
        return {"session_id": state.session_id, "state": state.model_dump()}
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/simulations/{session_id}/next")
async def simulation_next(session_id: str) -> dict[str, Any]:
    try:
        return await next_turn(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/simulations/{session_id}/user-turn")
async def simulation_user_turn(session_id: str, request: UserTurnRequest) -> dict[str, Any]:
    try:
        return await user_turn(session_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/simulations/{session_id}/suggestions")
def simulation_suggestions(session_id: str) -> dict[str, Any]:
    try:
        return {"suggestions": suggestions(session_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/simulations/{session_id}/next/stream")
async def simulation_next_stream(session_id: str) -> StreamingResponse:
    async def events():
        try:
            selected_speaker = next_speaker(session_id)
            yield f"event: agent_state\ndata: {json.dumps({'speaker_id': selected_speaker, 'agent': selected_speaker, 'status': 'thinking'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
            result = await next_turn(session_id)
            actual_speaker = (result.get("turn") or {}).get("speaker_agent_id")
            if actual_speaker != selected_speaker:
                logger.warning("SSE speaker mismatch session=%s selected=%s actual=%s", session_id, selected_speaker, actual_speaker)
            speech = (result.get("turn") or {}).get("message", "")
            yield f"event: agent_state\ndata: {json.dumps({'speaker_id': actual_speaker, 'agent': actual_speaker, 'status': 'speaking'}, ensure_ascii=False)}\n\n"
            for index in range(0, len(speech), 80):
                yield f"event: token\ndata: {json.dumps({'text': speech[index:index+80]}, ensure_ascii=False)}\n\n"
            yield f"event: evidence\ndata: {json.dumps({'evidence': (result.get('turn') or {}).get('evidence', [])}, ensure_ascii=False)}\n\n"
            yield f"event: state\ndata: {json.dumps({'state': result['state']}, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("simulation stream failed session=%s selected_speaker=%s error_type=%s", session_id, selected_speaker if "selected_speaker" in locals() else None, type(exc).__name__)
            yield f"event: error\ndata: {json.dumps({'message': 'AI 응답을 불러오지 못했습니다.', 'detail': str(exc)[:120]}, ensure_ascii=False)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/v1/simulations/{session_id}")
def simulation_get(session_id: str) -> dict[str, Any]:
    try:
        state = get_simulation(session_id)
        return {"session_id": session_id, "state": state.model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/simulations/{session_id}/state")
def simulation_state(session_id: str) -> dict[str, Any]:
    return simulation_get(session_id)


@app.get("/api/v1/simulations/{session_id}/evidence")
def simulation_evidence(session_id: str) -> dict[str, Any]:
    try:
        return {"session_id": session_id, "evidence": get_simulation_evidence(session_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/simulations/{session_id}/result")
def simulation_result(session_id: str) -> dict[str, Any]:
    result = get_simulation_result(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="simulation result not found")
    return {"session_id": session_id, "result": result}
