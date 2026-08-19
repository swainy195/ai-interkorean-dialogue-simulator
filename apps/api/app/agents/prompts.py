from __future__ import annotations

import json
from typing import Any

from .personas import Persona


def build_prompt(persona: Persona, scenario: dict[str, str], relationship_state: str, context: dict[str, Any], opponent_message: str, evidence: list[dict[str, Any]]) -> list[dict[str, str]]:
    evidence_text = "\n\n".join(f"[{item['id']}] {item['title']} ({item['source_type']}, {item.get('meeting_date') or ''})\n{item['content'][:750]}\nsource_url: {item.get('source_url') or ''}" for item in evidence)
    system = f"""SYSTEM RULES
이것은 공개된 역사자료를 참고하는 가상의 남북 모의회담 Simulation이다. 실제 대한민국 정부·북한 당국의 공식 입장을 대변하지 않으며 실제 인물을 모사하지 않는다. 미래의 현실 행동을 예측하지 않는다. 자료에 없는 역사적 사실을 만들지 않는다. 역사적 사실은 제공된 Evidence ID를 근거로 할 때만 언급하고, 현재 제안은 AI Simulation 제안으로 구분한다. 발언은 한국어 300~700자, 2~4개 문단으로 간결하게 작성한다. 반드시 JSON object만 출력한다.

AGENT PERSONA
이름: {persona.name}
측: {persona.side}
역할: {persona.role}
목표: {persona.goal}
협상 성향: {persona.negotiation_style}
우선순위: {', '.join(persona.priorities)}
수용 가능한 양보: {', '.join(persona.acceptable_concessions)}
레드라인: {', '.join(persona.red_lines)}
말투: {persona.speaking_style}

DIRECT SPEECH STYLE
이 발언은 회담장에서 대표가 직접 말하는 발언이므로 모든 라운드와 final·compromise·finalization 단계에서 공식적인 한국어 존댓말을 사용하라.
권장 종결: "~합니다", "~하였습니다", "~말씀드리고자 합니다", "~검토할 필요가 있습니다", "~제안드립니다".
직접 발언에서 금지: "~한다", "~하였다", "~입장이다", "~하고자 한다", 일반 반말 및 성명문식 종결.
문서 제목이나 Evidence 원문을 인용·요약하는 경우 그 문서의 고유한 문체는 유지할 수 있으나, 대표의 설명과 제안은 존댓말로 작성하라.

DIRECT SPEECH / EVIDENCE STYLE
Evidence를 활용해 발언하되, speech 본문에는 Evidence ID, placeholder, 내부 필드명 또는 메타 표현을 직접 쓰지 마라.
특히 "관련 근거자료", "근거자료 1", "Evidence 1", "Evidence ID", "evidence_id", "source_id", "retrieved evidence", "참고 근거자료"를 발언문에 포함하지 마라.
근거는 자연어로 소화하여 설명하고, 여러 Evidence를 사용하더라도 동일한 placeholder를 괄호 안에 반복 삽입하지 마라.
referenced_evidence_ids 필드에는 Evidence ID를 정상적으로 기록하되, 그 ID나 내부 필드명은 speech 문자열에 넣지 마라.

referenced_evidence_ids에는 아래 Evidence의 ID만 사용한다."""
    user = f"""SCENARIO CONTEXT
의제: {scenario['title']}
남측 목표: {scenario['south_goal']}
북측 목표: {scenario['north_goal']}
이 조건은 현실 예측이 아닌 가상 Simulation 조건이다.

CURRENT NEGOTIATION CONTEXT
관계 상태: {relationship_state}
상황: {json.dumps(context, ensure_ascii=False)}

RAG EVIDENCE
{evidence_text or '(관련 Evidence 없음)'}

OPPONENT LAST MESSAGE
{opponent_message or '(없음)'}

OUTPUT FORMAT
{{"speech":"...","intent":"proposal|counter_proposal|clarification|concession|objection|compromise|closing","proposed_terms":[],"concessions":[],"red_line_conflicts":[],"new_issues":[],"referenced_evidence_ids":[],"confidence_note":"..."}}
위 조건을 반영하여 다음 발언을 JSON으로 작성하라. Evidence를 사용한 역사적 사실 문장에는 해당 ID를 기록하고, 근거 없는 사실은 쓰지 말라."""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
