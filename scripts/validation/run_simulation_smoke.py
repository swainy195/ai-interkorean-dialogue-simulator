"""Run bounded AI-vs-AI Phase 7 simulations through the API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    scenarios = [("separated_families", 6), ("transport_cooperation", 6), ("military_tension", 6)]
    reports = []
    with TestClient(app) as client:
        for scenario, max_rounds in scenarios:
            created = client.post("/api/v1/simulations", json={"scenario": scenario, "relationship_state": "neutral", "mode": "AI_VS_AI", "max_rounds": max_rounds})
            created.raise_for_status()
            session_id = created.json()["session_id"]
            turns = []
            result = None
            while True:
                response = client.post(f"/api/v1/simulations/{session_id}/next")
                if response.status_code >= 400:
                    raise RuntimeError(f"{scenario} round {len(turns)+1} failed: {response.status_code} {response.text[:500]}")
                body = response.json()
                turns.append(body["turn"])
                result = body.get("result") or result
                if body["state"]["status"] != "RUNNING":
                    break
            state = client.get(f"/api/v1/simulations/{session_id}/state").json()["state"]
            evidence = client.get(f"/api/v1/simulations/{session_id}/evidence").json()["evidence"]
            stored_result = client.get(f"/api/v1/simulations/{session_id}/result").json()["result"]
            prompt_tokens = sum(int((turn.get("usage") or {}).get("prompt_tokens") or 0) for turn in turns)
            completion_tokens = sum(int((turn.get("usage") or {}).get("completion_tokens") or 0) for turn in turns)
            turn_cost = sum(float((turn.get("usage") or {}).get("cost") or 0) for turn in turns)
            moderator_calls = sum(1 for turn in turns if turn.get("moderator_usage"))
            moderator_fallbacks = sum(1 for turn in turns if (turn.get("moderator_usage") or {}).get("fallback"))
            moderator_prompt_tokens = sum(int((turn.get("moderator_usage") or {}).get("prompt_tokens") or 0) for turn in turns)
            moderator_completion_tokens = sum(int((turn.get("moderator_usage") or {}).get("completion_tokens") or 0) for turn in turns)
            moderator_cost = sum(float((turn.get("moderator_usage") or {}).get("cost") or 0) for turn in turns)
            evaluator_usage = (result or {}).get("usage") or {}
            report = {"scenario": scenario, "session_id": session_id, "rounds": len(turns), "final_status": state["status"], "phases": [turn["phase"] for turn in turns], "speakers": [turn["speaker_agent_id"] for turn in turns], "agreements": state["agreements"], "unresolved": state["unresolved_issues"], "evidence_rows": len(evidence), "used_evidence_ids": state["used_evidence_ids"], "moderator_calls": moderator_calls, "moderator_fallbacks": moderator_fallbacks, "prompt_tokens": prompt_tokens + moderator_prompt_tokens + int(evaluator_usage.get("prompt_tokens") or 0), "completion_tokens": completion_tokens + moderator_completion_tokens + int(evaluator_usage.get("completion_tokens") or 0), "total_tokens": prompt_tokens + completion_tokens + moderator_prompt_tokens + moderator_completion_tokens + int(evaluator_usage.get("total_tokens") or 0), "total_cost": turn_cost + moderator_cost + float(evaluator_usage.get("cost") or 0), "evaluator_result_type": stored_result["result_type"], "evaluator_fallback": bool(evaluator_usage.get("fallback")), "summary": stored_result["summary"]}
            reports.append(report)
    print(json.dumps({"simulations": reports}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
