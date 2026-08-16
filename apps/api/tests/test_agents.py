from app.agents.personas import PERSONAS, get_persona
from app.agents.prompts import build_prompt
from app.agents.scenarios import SCENARIOS, get_scenario
from app.agents.service import parse_json_object, select_evidence
from app.agents.schemas import AgentResponse


def test_personas_and_scenarios_load() -> None:
    assert set(PERSONAS) == {"south_chief", "south_working", "north_chief", "north_working"}
    assert set(SCENARIOS) == {"separated_families", "transport_cooperation", "military_tension"}
    assert get_persona("south_working").role == "실무대표"
    assert get_scenario("separated_families")["title"] == "이산가족 상봉 재개"


def test_prompt_contains_ordered_sections_and_evidence_ids() -> None:
    messages = build_prompt(get_persona("south_chief"), get_scenario("separated_families"), "neutral", {}, "테스트 발언", [{"id": "E1", "title": "합의", "source_type": "agreement", "meeting_date": "2005", "content": "내용", "source_url": ""}])
    text = messages[0]["content"] + messages[1]["content"]
    assert text.index("SYSTEM RULES") < text.index("AGENT PERSONA") < text.index("SCENARIO CONTEXT") < text.index("RAG EVIDENCE") < text.index("OPPONENT LAST MESSAGE") < text.index("OUTPUT FORMAT")
    assert "E1" in text


def test_structured_response_and_invalid_intent_rejected() -> None:
    parsed = AgentResponse.model_validate(parse_json_object('```json\n{"speech":"제안합니다.","intent":"proposal","referenced_evidence_ids":["E1"]}\n```'))
    assert parsed.intent == "proposal"
    try:
        AgentResponse.model_validate({"speech": "x", "intent": "invalid"})
    except Exception:
        pass
    else:
        raise AssertionError("invalid intent accepted")


def test_evidence_selection_limits_document_and_assigns_ids() -> None:
    rows = [{"id": "u1", "document_id": "d1", "source_type": "meeting", "similarity": 0.9, "title": "a"}, {"id": "u2", "document_id": "d1", "source_type": "meeting", "similarity": 0.8, "title": "b"}, {"id": "u3", "document_id": "d2", "source_type": "agreement", "similarity": 0.7, "title": "c"}]
    selected = select_evidence(rows, 5)
    assert [row["id"] for row in selected] == ["E1", "E2", "E3"]
    assert sum(row["document_id"] == "d1" for row in selected) == 2
