from __future__ import annotations

import json
from typing import Any

from app.agents.service import chat, parse_json_object

from .schemas import EvaluatorResult, SimulationState


async def evaluate(state: SimulationState, turns: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    compact_turns = [{"speaker": t["speaker_agent_id"], "intent": t["intent"], "message": t["message"][:500]} for t in turns[-8:]]
    prompt = [{"role": "system", "content": "당신은 가상 남북 모의회담의 종료 평가 Agent다. 실제 북한의 수용 가능성이나 미래를 예측하지 말라. JSON object만 출력하라. 필수 필드만 사용한다: result_type(AGREEMENT|PARTIAL_AGREEMENT|BREAKDOWN), summary, agreements[], unresolved_issues[], follow_up_items[]. 배열은 문자열만 넣는다."}, {"role": "user", "content": json.dumps({"scenario": state.scenario_id, "status": state.status, "agreements": state.agreements[-8:], "unresolved_issues": state.unresolved_issues[-8:], "concessions": state.concessions[-6:], "turns": compact_turns[-4:], "evidence": [{"title": e.get("title"), "source_type": e.get("source_type")} for e in evidence[:6]]}, ensure_ascii=False)}]
    try:
        raw, usage = await chat(prompt)
        result = EvaluatorResult.model_validate(raw).model_dump()
        return result, usage
    except (RuntimeError, ValueError, TypeError):
        # The evaluator call is attempted once, but a malformed model object
        # must not discard the already-persisted simulation state.
        fallback = EvaluatorResult(
            result_type=state.status if state.status in {"AGREEMENT", "PARTIAL_AGREEMENT", "BREAKDOWN"} else "PARTIAL_AGREEMENT",
            summary=f"{state.scenario_id} 회담은 {state.current_round}개 턴 후 내부 상태값에 따라 종료되었다.",
            south_position=state.proposals[:5],
            north_position=state.counter_proposals[:5],
            agreements=state.agreements[:10],
            unresolved_issues=state.unresolved_issues[:10],
            south_concessions=state.concessions[:5],
            north_concessions=[],
            follow_up_items=state.unresolved_issues[:5],
            evidence_summary=list(dict.fromkeys(item.get("title", "") for item in evidence if item.get("title")))[:10],
        ).model_dump()
        return fallback, {"fallback": True}
