from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PHASES = ("OPENING", "AGENDA", "PROPOSAL", "RESPONSE", "ISSUE_IDENTIFICATION", "NEGOTIATION", "COMPROMISE", "FINALIZATION")
STATUSES = ("RUNNING", "AGREEMENT", "PARTIAL_AGREEMENT", "BREAKDOWN")


class SimulationCreate(BaseModel):
    scenario: str
    relationship_state: str = "neutral"
    mode: Literal["AI_VS_AI", "USER_SOUTH_VS_AI_NORTH"] = "AI_VS_AI"
    max_rounds: int = Field(default=8, ge=4, le=8)


class SimulationState(BaseModel):
    session_id: str
    scenario_id: str
    mode: str = "AI_VS_AI"
    current_round: int = 0
    max_rounds: int = 8
    current_phase: str = "OPENING"
    active_speaker: str = "south_chief"
    issues: list[str] = Field(default_factory=list)
    proposals: list[str] = Field(default_factory=list)
    counter_proposals: list[str] = Field(default_factory=list)
    concessions: list[str] = Field(default_factory=list)
    agreements: list[str] = Field(default_factory=list)
    candidate_agreements: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    critical_red_line_conflicts: list[str] = Field(default_factory=list)
    repeated_rejections: int = 0
    moderator_calls: int = 0
    used_evidence_ids: list[str] = Field(default_factory=list)
    tension_level: int = Field(default=0, ge=0, le=100)
    agreement_level: int = Field(default=45, ge=0, le=100)
    conversation_summary: str = ""
    status: Literal["RUNNING", "AGREEMENT", "PARTIAL_AGREEMENT", "BREAKDOWN"] = "RUNNING"


class EvaluatorResult(BaseModel):
    result_type: Literal["AGREEMENT", "PARTIAL_AGREEMENT", "BREAKDOWN"]
    summary: str
    south_position: list[str] = Field(default_factory=list)
    north_position: list[str] = Field(default_factory=list)
    agreements: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    south_concessions: list[str] = Field(default_factory=list)
    north_concessions: list[str] = Field(default_factory=list)
    follow_up_items: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)


class SimulationNextResponse(BaseModel):
    state: SimulationState
    turn: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


class UserTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
