from __future__ import annotations

import re
from typing import Any

from app.agents.schemas import AgentRequest
from app.agents.scenarios import get_scenario
from app.agents.service import respond

from .schemas import PHASES, SimulationState

SPEAKERS = ["south_chief", "north_chief", "south_working", "north_working"]
PHASE_BY_ROUND = {1: "OPENING", 2: "AGENDA", 3: "PROPOSAL", 4: "RESPONSE", 5: "NEGOTIATION", 6: "COMPROMISE", 7: "FINALIZATION", 8: "FINALIZATION"}


def choose_speaker(round_number: int, previous_intent: str | None = None) -> str:
    if round_number <= 4:
        return SPEAKERS[round_number - 1]
    if previous_intent in {"proposal", "counter_proposal", "objection"}:
        return "south_working" if round_number % 2 else "north_working"
    return "south_chief" if round_number % 2 else "north_chief"


def next_phase(round_number: int, status: str = "RUNNING") -> str:
    if status != "RUNNING":
        return status
    return PHASE_BY_ROUND.get(min(round_number, 8), "NEGOTIATION")


def update_state(state: SimulationState, response: dict[str, Any], speaker: str) -> SimulationState:
    structured = response["response"]
    intent = structured["intent"]
    state.current_round += 1
    state.active_speaker = speaker
    state.current_phase = next_phase(state.current_round)
    new_terms = structured.get("proposed_terms", [])
    prior_terms = state.proposals[-6:] + state.counter_proposals[-6:]
    if intent == "proposal":
        state.proposals.extend(new_terms)
    elif intent == "counter_proposal":
        state.counter_proposals.extend(new_terms)
    state.concessions.extend(structured.get("concessions", []))
    state.issues.extend(structured.get("new_issues", []))
    red_lines = structured.get("red_line_conflicts", [])
    state.unresolved_issues.extend(red_lines)
    state.used_evidence_ids.extend(item["id"] for item in response.get("evidence", []) if item["id"] in structured.get("referenced_evidence_ids", []))
    def tokens(value: str) -> set[str]:
        return set(re.findall(r"[가-힣A-Za-z0-9]{2,}", value.lower()))

    overlaps = []
    for current in new_terms:
        current_tokens = tokens(current)
        for previous in prior_terms:
            if len(current_tokens & tokens(previous)) >= 2:
                overlaps.append(current)
                break
    state.candidate_agreements.extend(overlaps)
    if overlaps and intent in {"concession", "compromise", "counter_proposal"}:
        state.agreements.extend(overlaps)
        state.agreement_level += 12
    if intent in {"concession", "compromise"}:
        state.agreement_level += 8
        state.tension_level -= 8
    elif intent in {"proposal", "counter_proposal"}:
        state.agreement_level += 2
    elif intent == "objection":
        state.agreement_level -= 2
        state.tension_level += 4
        state.repeated_rejections += 1
    if red_lines:
        state.tension_level += 5
        if any(item in state.unresolved_issues[:-len(red_lines)] for item in red_lines):
            state.critical_red_line_conflicts.extend(red_lines)
    if state.proposals and state.concessions and state.current_round >= 5:
        state.candidate_agreements.append("단계적 후속 실무협의 가능성")
    state.agreement_level = max(0, min(100, state.agreement_level))
    state.tension_level = max(0, min(100, state.tension_level))
    state.used_evidence_ids = list(dict.fromkeys(state.used_evidence_ids))
    state.unresolved_issues = list(dict.fromkeys(state.unresolved_issues))
    state.agreements = list(dict.fromkeys(state.agreements))
    state.candidate_agreements = list(dict.fromkeys(state.candidate_agreements))
    state.critical_red_line_conflicts = list(dict.fromkeys(state.critical_red_line_conflicts))
    return state


def end_status(state: SimulationState) -> str | None:
    if state.tension_level >= 85 or len(state.critical_red_line_conflicts) >= 2 or (state.repeated_rejections >= 3 and not state.candidate_agreements):
        return "BREAKDOWN"
    if state.current_round < state.max_rounds:
        return None
    if state.agreement_level >= 65 and not state.unresolved_issues and not state.critical_red_line_conflicts:
        return "AGREEMENT"
    if state.agreement_level >= 35 and (state.agreements or state.candidate_agreements or state.concessions) and not state.critical_red_line_conflicts:
        return "PARTIAL_AGREEMENT"
    return "BREAKDOWN"


def deterministic_summary(state: SimulationState, turns: list[dict[str, Any]]) -> str:
    recent = turns[-3:]
    names = ", ".join(item["speaker_agent_id"] for item in recent)
    return f"{state.scenario_id} 의제에서 {state.current_round}개 발언을 진행했다. 최근 발언자: {names}. 제안 {len(state.proposals)}건, 양보 {len(state.concessions)}건, 합의 후보 {len(state.agreements)}건, 미해결 쟁점 {len(state.unresolved_issues)}건이다."


async def run_agent_turn(state: SimulationState, turns: list[dict[str, Any]], relationship_state: str, forced_speaker: str | None = None) -> tuple[str, dict[str, Any]]:
    speaker = forced_speaker or choose_speaker(state.current_round + 1, turns[-1]["intent"] if turns else None)
    scenario = get_scenario(state.scenario_id)
    opponent = turns[-1]["message"] if turns else "회담을 시작하겠습니다."
    context = {"phase": next_phase(state.current_round + 1), "current_phase": next_phase(state.current_round + 1), "current_round": state.current_round + 1, "max_rounds": state.max_rounds, "previous_speaker": turns[-1]["speaker_agent_id"] if turns else None, "previous_turn": opponent, "previous_intent": turns[-1].get("intent") if turns else None, "active_issues": state.issues[-4:], "current_agreements": state.agreements[-3:], "current_unresolved": state.unresolved_issues[-4:], "latest_proposal": (state.proposals + [""])[-1], "latest_counterproposal": (state.counter_proposals + [""])[-1], "summary": state.conversation_summary[-700:], "instruction": "최근 2개 발언과 동일한 주장을 반복하지 말고 수정안·조건부 수용·일정 조정·절차 제안 중 하나로 진전시켜라."}
    opponent = opponent[-750:]
    result = await respond(AgentRequest(agent=speaker, scenario=state.scenario_id, relationship_state=relationship_state, opponent_message=opponent, negotiation_context=context))
    return speaker, result
