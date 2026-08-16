from app.simulation.engine import choose_speaker, end_status, next_phase, update_state
from app.simulation.schemas import SimulationState


def test_speaker_and_phase_sequence() -> None:
    assert [choose_speaker(i) for i in range(1, 5)] == ["south_chief", "north_chief", "south_working", "north_working"]
    assert [next_phase(i) for i in range(1, 7)] == ["OPENING", "AGENDA", "PROPOSAL", "RESPONSE", "NEGOTIATION", "COMPROMISE"]


def test_state_updater_and_end_condition() -> None:
    state = SimulationState(session_id="s", scenario_id="separated_families", current_round=4, agreement_level=50)
    result = {"response": {"intent": "concession", "proposed_terms": ["단계적 시행"], "counter_proposals": [], "concessions": ["일정 조정"], "new_issues": [], "red_line_conflicts": [], "referenced_evidence_ids": ["E1"]}, "evidence": [{"id": "E1"}]}
    state = update_state(state, result, "south_working")
    assert state.current_round == 5
    assert state.concessions == ["일정 조정"]
    assert state.agreement_level > 50
    state.current_round = state.max_rounds
    assert end_status(state) in {"AGREEMENT", "PARTIAL_AGREEMENT", "BREAKDOWN"}


def test_terminal_state_is_not_running() -> None:
    state = SimulationState(session_id="s", scenario_id="military_tension", current_round=8, max_rounds=8, agreement_level=10, tension_level=90)
    assert end_status(state) == "BREAKDOWN"


def test_terminal_branch_fixtures() -> None:
    agreement = SimulationState(session_id="a", scenario_id="separated_families", current_round=6, max_rounds=6, agreement_level=75, agreements=["상봉 일정"], unresolved_issues=[])
    partial = SimulationState(session_id="b", scenario_id="transport_cooperation", current_round=6, max_rounds=6, agreement_level=48, agreements=["공동조사"], unresolved_issues=["세부 일정"])
    breakdown = SimulationState(session_id="c", scenario_id="military_tension", current_round=6, max_rounds=6, agreement_level=50, critical_red_line_conflicts=["핵심 선결조건"], unresolved_issues=["핵심 선결조건"])
    assert end_status(agreement) == "AGREEMENT"
    assert end_status(partial) == "PARTIAL_AGREEMENT"
    assert end_status(breakdown) == "BREAKDOWN"
