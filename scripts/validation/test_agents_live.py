"""Live Phase 6 agent smoke tests; never prints API credentials."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.agents.schemas import AgentRequest  # noqa: E402
from app.agents.service import respond  # noqa: E402
from app.config import get_settings  # noqa: E402


CASES = [
    ("south_chief", "separated_families"),
    ("south_working", "separated_families"),
    ("north_chief", "separated_families"),
    ("north_working", "separated_families"),
    ("south_chief", "transport_cooperation"),
    ("north_chief", "military_tension"),
]


async def main() -> None:
    results = []
    total_prompt = total_completion = total_tokens = 0
    for agent, scenario in CASES:
        result = await respond(AgentRequest(agent=agent, scenario=scenario, relationship_state="neutral", opponent_message="상대측은 상호 관심사항을 고려하면서 단계적으로 협의하자는 입장입니다.", negotiation_context={"turn": 1, "test": True}))
        evidence_ids = {item["id"] for item in result["evidence"]}
        referenced = set(result["response"]["referenced_evidence_ids"])
        usage = result.get("usage") or {}
        total_prompt += int(usage.get("prompt_tokens") or 0)
        total_completion += int(usage.get("completion_tokens") or 0)
        total_tokens += int(usage.get("total_tokens") or 0)
        results.append({"agent": agent, "scenario": scenario, "name": result["agent"]["name"], "role": result["agent"]["role"], "intent": result["response"]["intent"], "speech_length": len(result["response"]["speech"]), "evidence_count": len(result["evidence"]), "referenced_evidence_ids": result["response"]["referenced_evidence_ids"], "invalid_evidence_ids": sorted(referenced - evidence_ids), "usage": usage})
    report = {"model": get_settings().openrouter_chat_model, "calls": len(results), "prompt_tokens": total_prompt, "completion_tokens": total_completion, "total_tokens": total_tokens, "results": results}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any(row["invalid_evidence_ids"] for row in results) or len(results) < 6:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
