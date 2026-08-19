from __future__ import annotations

import uuid
from typing import Any

from app.agents.scenarios import get_scenario

from .engine import choose_speaker, deterministic_summary, run_agent_turn, update_state
from .evaluator import evaluate
from .moderator import call_moderator, moderate, moderator_trigger
from .repository import create_session, fetch_evidence, fetch_result, load_session, load_turns, save_result, save_turn
from .schemas import SimulationCreate, SimulationState, UserTurnRequest


def create(request: SimulationCreate) -> SimulationState:
    get_scenario(request.scenario)
    state = SimulationState(session_id=str(uuid.uuid4()), scenario_id=request.scenario, mode=request.mode, max_rounds=request.max_rounds, agreement_level={"improving": 55, "tense": 30}.get(request.relationship_state, 45))
    create_session(state, request.relationship_state)
    return state


async def next_turn(session_id: str) -> dict[str, Any]:
    state, relationship = load_session(session_id)
    if state.mode != "AI_VS_AI":
        raise ValueError("use user-turn for USER_SOUTH_VS_AI_NORTH sessions")
    if state.status != "RUNNING":
        raise ValueError(f"session is terminal: {state.status}")
    turns = load_turns(session_id)
    speaker, response = await run_agent_turn(state, turns, relationship)
    state = update_state(state, response, speaker)
    state.conversation_summary = deterministic_summary(state, turns + [{"speaker_agent_id": speaker, "message": response["response"]["speech"], "intent": response["response"]["intent"]}])
    recommendation = moderate(state, response)
    moderator_result = None
    moderator_usage: dict[str, Any] = {}
    if moderator_trigger(state, response):
        state.moderator_calls += 1
        moderator_result, moderator_usage = await call_moderator(state, response)
    if recommendation["should_end"] or state.current_round >= state.max_rounds:
        state.status = recommendation["recommended_result"] or "PARTIAL_AGREEMENT"
    turn = save_turn(state, speaker, response, response["evidence"])
    turn["moderator_usage"] = moderator_usage
    result = None
    if state.status != "RUNNING":
        all_evidence = fetch_evidence(session_id)
        evaluated, usage = await evaluate(state, turns + [turn], all_evidence)
        evaluated["result_type"] = state.status
        save_result(session_id, evaluated)
        result = {**evaluated, "usage": usage}
    return {"state": state.model_dump(), "turn": turn, "result": result, "moderator": moderator_result or recommendation, "moderator_usage": moderator_usage}


def next_speaker(session_id: str) -> str:
    state, _ = load_session(session_id)
    turns = load_turns(session_id)
    return choose_speaker(state.current_round + 1, turns[-1]["intent"] if turns else None)


async def user_turn(session_id: str, request: UserTurnRequest) -> dict[str, Any]:
    state, relationship = load_session(session_id)
    if state.mode != "USER_SOUTH_VS_AI_NORTH":
        raise ValueError("user-turn is available only in USER_SOUTH_VS_AI_NORTH mode")
    if state.status != "RUNNING":
        raise ValueError(f"session is terminal: {state.status}")
    user_structured = {"speech": request.message, "intent": "proposal", "proposed_terms": [request.message], "concessions": [], "red_line_conflicts": [], "new_issues": [], "referenced_evidence_ids": [], "confidence_note": "사용자 원문 발언"}
    user_result = {"response": user_structured, "evidence": [], "usage": {}}
    state = update_state(state, user_result, "south_chief")
    turns = load_turns(session_id)
    user_saved = save_turn(state, "south_chief", user_result, [])
    turns.append(user_saved)
    speaker, response = await run_agent_turn(state, turns, relationship, forced_speaker="north_chief" if state.current_round % 2 else "north_working")
    state = update_state(state, response, speaker)
    state.conversation_summary = deterministic_summary(state, turns + [{"speaker_agent_id": speaker, "message": response["response"]["speech"], "intent": response["response"]["intent"]}])
    recommendation = moderate(state, response)
    moderator_usage: dict[str, Any] = {}
    moderator_result = None
    if moderator_trigger(state, response):
        state.moderator_calls += 1
        moderator_result, moderator_usage = await call_moderator(state, response)
    if recommendation["should_end"] or state.current_round >= state.max_rounds:
        state.status = recommendation["recommended_result"] or "PARTIAL_AGREEMENT"
    ai_saved = save_turn(state, speaker, response, response["evidence"])
    ai_saved["moderator_usage"] = moderator_usage
    result = None
    if state.status != "RUNNING":
        all_evidence = fetch_evidence(session_id)
        evaluated, usage = await evaluate(state, turns + [ai_saved], all_evidence)
        evaluated["result_type"] = state.status
        save_result(session_id, evaluated)
        result = {**evaluated, "usage": usage}
    return {"state": state.model_dump(), "turn": ai_saved, "user_turn": user_saved, "result": result, "moderator": moderator_result or recommendation, "moderator_usage": moderator_usage}


def suggestions(session_id: str) -> list[str]:
    state, _ = load_session(session_id)
    templates = {
        "separated_families": ["단계적 이산가족 상봉 재개를 위한 실무협의체를 구성하자고 제안합니다.", "생사확인과 상봉 대상자 명단 교환부터 우선 추진하자고 제안합니다.", "화상상봉을 먼저 실시하고 대면상봉으로 확대하자고 제안합니다."],
        "transport_cooperation": ["공동조사단 구성과 조사 일정을 먼저 확정하자고 제안합니다.", "철도·도로 연결을 위한 단계별 실무협의체를 구성하자고 제안합니다.", "안전·검증 절차를 합의한 뒤 시범구간 공동조사를 시작하자고 제안합니다."],
        "military_tension": ["우발충돌 방지를 위한 연락체계 복원부터 논의하자고 제안합니다.", "상호 통보와 검증이 가능한 단계적 신뢰구축 조치를 제안합니다.", "군사당국 실무협의체에서 세부 이행 일정을 확정하자고 제안합니다."],
    }
    return templates[state.scenario_id]


def get(session_id: str) -> SimulationState:
    return load_session(session_id)[0]


def get_result(session_id: str) -> dict[str, Any] | None:
    return fetch_result(session_id)


def get_evidence(session_id: str) -> list[dict[str, Any]]:
    return fetch_evidence(session_id)
