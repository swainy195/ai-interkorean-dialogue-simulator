"""Replay the latest Phase 7.1 sessions and print round-level state transitions."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

from sys import path
path.insert(0, str(ROOT / "apps" / "api"))
from app.simulation.engine import end_status, update_state  # noqa: E402
from app.simulation.schemas import SimulationState  # noqa: E402


def main() -> None:
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn, conn.cursor() as cur:
        cur.execute("select id::text,scenario_id,max_rounds from public.simulation_sessions where id in ('98b827a7-7cf6-497c-89e8-b8db9761ac75','f50b09fa-76ea-43d2-98bd-a491da93d467','adc49c05-ad7e-4ea4-b61f-2922fbbefcce') order by scenario_id")
        sessions = cur.fetchall()
        output = []
        for session_id, scenario, max_rounds in sessions:
            cur.execute("select round,speaker_agent_id,structured_response from public.simulation_turns where session_id=%s order by round", (session_id,))
            state = SimulationState(session_id=session_id, scenario_id=scenario, max_rounds=max_rounds)
            transitions = []
            for round_number, speaker, structured in cur.fetchall():
                response = {"response": structured, "evidence": [{"id": evidence_id} for evidence_id in structured.get("referenced_evidence_ids", [])]}
                state = update_state(state, response, speaker)
                transitions.append({"round": round_number, "speaker": speaker, "agreement_level": state.agreement_level, "tension_level": state.tension_level, "issues": len(state.issues), "candidate_agreements": len(state.candidate_agreements), "agreements": len(state.agreements), "unresolved": len(state.unresolved_issues), "critical_red_lines": len(state.critical_red_line_conflicts), "intent": structured.get("intent")})
            output.append({"scenario": scenario, "transitions": transitions, "final_status_from_replay": end_status(state), "final_agreement_level": state.agreement_level, "final_tension_level": state.tension_level, "final_reason": "critical conflict/repeated rejection" if state.critical_red_line_conflicts or state.repeated_rejections >= 3 else ("agreement with no unresolved issues" if state.agreement_level >= 65 and not state.unresolved_issues else "partial progress or insufficient agreement at max rounds")})
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
