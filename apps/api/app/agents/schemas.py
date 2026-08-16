from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Intent = Literal["proposal", "counter_proposal", "clarification", "concession", "objection", "compromise", "closing"]


class AgentRequest(BaseModel):
    agent: str
    scenario: str
    relationship_state: str = "neutral"
    opponent_message: str = ""
    negotiation_context: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    speech: str = Field(min_length=1, max_length=2000)
    intent: Intent
    proposed_terms: list[str] = Field(default_factory=list)
    concessions: list[str] = Field(default_factory=list)
    red_line_conflicts: list[str] = Field(default_factory=list)
    new_issues: list[str] = Field(default_factory=list)
    referenced_evidence_ids: list[str] = Field(default_factory=list)
    confidence_note: str = ""

    @field_validator("intent", mode="before")
    @classmethod
    def normalize_intent(cls, value: Any) -> Any:
        aliases = {"conditional_acceptance": "concession", "acceptance": "concession", "reject": "objection", "question": "clarification", "counterproposal": "counter_proposal"}
        return aliases.get(str(value), value)

    @field_validator("proposed_terms", "concessions", "red_line_conflicts", "new_issues", mode="before")
    @classmethod
    def normalize_list_items(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("field must be a list")
        normalized = []
        for item in value:
            if isinstance(item, dict):
                normalized.append("; ".join(f"{key}: {val}" for key, val in item.items()))
            else:
                normalized.append(str(item))
        return normalized

    @field_validator("referenced_evidence_ids")
    @classmethod
    def unique_ids(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))
