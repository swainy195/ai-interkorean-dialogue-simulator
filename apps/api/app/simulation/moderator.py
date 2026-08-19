from __future__ import annotations

from typing import Any

from app.agents.service import chat, parse_json_object

from .engine import end_status, next_phase
from .schemas import SimulationState


def moderate(state: SimulationState, last_response: dict[str, Any] | None = None) -> dict[str, Any]:
    intent = (last_response or {}).get("response", {}).get("intent")
    repetition = False
    if last_response:
        text = last_response["response"].get("speech", "")
        repetition = any(text and text[:60] in item for item in state.conversation_summary.split(" | "))
    recommendation = end_status(state)
    return {"recommended_phase": next_phase(state.current_round + 1) if state.status == "RUNNING" else state.status, "recommended_next_speaker": None, "issues": [{"name": item, "status": "open"} for item in state.unresolved_issues[-10:]], "agreements_detected": state.agreements[-10:], "unresolved_issues": state.unresolved_issues[-10:], "repetition_detected": repetition, "should_end": recommendation is not None, "recommended_result": recommendation, "reason": f"deterministic state review after intent={intent or 'none'}"}


def moderator_trigger(state: SimulationState, last_response: dict[str, Any] | None = None) -> bool:
    intent = (last_response or {}).get("response", {}).get("intent")
    return state.moderator_calls < 2 and (state.current_round >= 4 or bool(state.candidate_agreements) or bool(state.critical_red_line_conflicts) or intent in {"compromise", "objection"})


async def call_moderator(state: SimulationState, last_response: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    deterministic = moderate(state, last_response)
    prompt = [{"role": "system", "content": "당신은 가상 남북 모의회담의 Moderator다. 정책이나 새 협상안을 만들지 말고 제공된 state만 해석하라. 실제 정부 입장이나 미래를 예측하지 않는다. state와 last_response에 있는 지명·시설명·기관명·회담명·날짜·숫자는 그대로 유지하고 새 역사적 명칭을 만들거나 다른 명칭으로 바꾸지 마라. JSON만 출력한다. 필드: recommended_phase, issues[], agreements_detected[], unresolved_issues[], repetition_detected, should_end, recommended_result(null|AGREEMENT|PARTIAL_AGREEMENT|BREAKDOWN), reason."}, {"role": "user", "content": str({"state": state.model_dump(), "last_response": (last_response or {}).get("response", {})})}]
    try:
        raw, usage = await chat(prompt)
        parsed = parse_json_object(raw) if isinstance(raw, str) else raw
        parsed["recommended_phase"] = parsed.get("recommended_phase", deterministic["recommended_phase"])
        if parsed["recommended_phase"] not in {"OPENING", "AGENDA", "PROPOSAL", "RESPONSE", "ISSUE_IDENTIFICATION", "NEGOTIATION", "COMPROMISE", "FINALIZATION", "AGREEMENT", "PARTIAL_AGREEMENT", "BREAKDOWN"}:
            parsed["recommended_phase"] = deterministic["recommended_phase"]
        return {**deterministic, **parsed, "source": "llm"}, usage
    except (RuntimeError, ValueError, TypeError):
        return {**deterministic, "source": "deterministic_fallback"}, {"fallback": True}
