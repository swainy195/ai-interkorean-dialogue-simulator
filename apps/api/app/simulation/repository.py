from __future__ import annotations

import json
import uuid
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.config import get_settings

from .schemas import SimulationState


def connect() -> psycopg.Connection:
    return psycopg.connect(get_settings().supabase_db_url, connect_timeout=20)


def create_session(state: SimulationState, relationship_state: str) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("insert into public.simulation_sessions (id,scenario_id,mode,status,current_round,max_rounds,current_phase,active_agent_id,negotiation_state,conversation_summary) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (state.session_id, state.scenario_id, state.mode, state.status, state.current_round, state.max_rounds, state.current_phase, state.active_speaker, Jsonb({**state.model_dump(), "relationship_state": relationship_state}), state.conversation_summary))
        conn.commit()


def load_session(session_id: str) -> tuple[SimulationState, str]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("select scenario_id,mode,status,current_round,max_rounds,current_phase,active_agent_id,negotiation_state,conversation_summary from public.simulation_sessions where id=%s", (session_id,))
        row = cur.fetchone()
        if not row:
            raise KeyError("simulation session not found")
        data = dict(row[7] or {})
        data.update({"session_id": session_id, "scenario_id": row[0], "mode": row[1], "status": row[2], "current_round": row[3], "max_rounds": row[4], "current_phase": row[5], "active_speaker": row[6] or "south_chief", "conversation_summary": row[8] or ""})
        relationship = data.pop("relationship_state", "neutral")
        return SimulationState.model_validate(data), relationship


def load_turns(session_id: str) -> list[dict[str, Any]]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("select id::text,round,speaker_agent_id,message,intent,phase,structured_response from public.simulation_turns where session_id=%s order by round", (session_id,))
        return [{"id": row[0], "round": row[1], "speaker_agent_id": row[2], "message": row[3], "intent": row[4], "phase": row[5], "structured_response": row[6]} for row in cur.fetchall()]


def save_turn(state: SimulationState, speaker: str, result: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("update public.simulation_sessions set status=%s,current_round=%s,current_phase=%s,active_agent_id=%s,negotiation_state=%s,conversation_summary=%s,ended_at=case when %s <> 'RUNNING' then now() else ended_at end where id=%s", (state.status, state.current_round, state.current_phase, speaker, Jsonb(state.model_dump()), state.conversation_summary, state.status, state.session_id))
        cur.execute("insert into public.simulation_turns (session_id,round,speaker_agent_id,message,intent,phase,structured_response) values (%s,%s,%s,%s,%s,%s,%s) returning id::text", (state.session_id, state.current_round, speaker, result["response"]["speech"], result["response"]["intent"], state.current_phase, Jsonb(result["response"])))
        turn_id = cur.fetchone()[0]
        cur.executemany("insert into public.simulation_evidence (session_id,turn_id,document_chunk_id,similarity,rank) values (%s,%s,%s,%s,%s) on conflict (turn_id,document_chunk_id) do nothing", [(state.session_id, turn_id, item["chunk_id"], item["similarity"], index) for index, item in enumerate(evidence, 1)])
        conn.commit()
    return {"id": turn_id, "round": state.current_round, "speaker_agent_id": speaker, "message": result["response"]["speech"], "intent": result["response"]["intent"], "phase": state.current_phase, "structured_response": result["response"], "evidence": evidence, "usage": result.get("usage") or {}}


def save_result(session_id: str, result: dict[str, Any]) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("insert into public.simulation_results (session_id,result_type,summary,south_position,north_position,agreements,unresolved_issues,follow_up_items,evaluation) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (session_id) do update set result_type=excluded.result_type,summary=excluded.summary,south_position=excluded.south_position,north_position=excluded.north_position,agreements=excluded.agreements,unresolved_issues=excluded.unresolved_issues,follow_up_items=excluded.follow_up_items,evaluation=excluded.evaluation", (session_id, result["result_type"], result["summary"], Jsonb(result.get("south_position", [])), Jsonb(result.get("north_position", [])), Jsonb(result.get("agreements", [])), Jsonb(result.get("unresolved_issues", [])), Jsonb(result.get("follow_up_items", [])), Jsonb(result)))
        conn.commit()


def fetch_result(session_id: str) -> dict[str, Any] | None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("select result_type,summary,south_position,north_position,agreements,unresolved_issues,follow_up_items,evaluation from public.simulation_results where session_id=%s", (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {"result_type": row[0], "summary": row[1], "south_position": row[2], "north_position": row[3], "agreements": row[4], "unresolved_issues": row[5], "follow_up_items": row[6], "evaluation": row[7]}


def fetch_evidence(session_id: str) -> list[dict[str, Any]]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("select se.turn_id::text,se.document_chunk_id::text,se.similarity,se.rank,dc.document_id,dc.title,dc.source_type,dc.source_url,dc.meeting_date from public.simulation_evidence se join public.document_chunks dc on dc.id=se.document_chunk_id where se.session_id=%s order by se.turn_id,se.rank", (session_id,))
        return [{"turn_id": r[0], "document_chunk_id": r[1], "similarity": r[2], "rank": r[3], "document_id": r[4], "title": r[5], "source_type": r[6], "source_url": r[7], "meeting_date": r[8].isoformat() if r[8] else None} for r in cur.fetchall()]
