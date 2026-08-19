from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx
import logging

from app.config import get_settings

from .personas import get_persona
from .prompts import build_prompt
from .repository import search_chunks
from .scenarios import get_scenario
from .schemas import AgentRequest, AgentResponse


logger = logging.getLogger(__name__)


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError("model response is not a JSON object")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("model response must be a JSON object")
    return value


def select_evidence(candidates: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    per_document: dict[str, int] = {}
    prioritized = sorted(candidates, key=lambda row: (row["source_type"] not in {"agreement", "agreement_commentary"}, -row["similarity"]))
    for row in prioritized:
        if per_document.get(row["document_id"], 0) >= 2:
            continue
        selected.append(row)
        per_document[row["document_id"]] = per_document.get(row["document_id"], 0) + 1
        if len(selected) == limit:
            break
    return [{**row, "chunk_id": row["id"], "id": f"E{index}"} for index, row in enumerate(selected, 1)]


async def embed_query(text: str) -> list[float]:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post("https://openrouter.ai/api/v1/embeddings", headers=headers, json={"model": settings.openrouter_embedding_model, "input": text})
        response.raise_for_status()
        vector = (response.json().get("data") or [])[0].get("embedding")
        if not isinstance(vector, list) or len(vector) != 2048:
            raise ValueError("query embedding dimension is not 2048")
        return vector


async def chat(messages: list[dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any]]:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json", "HTTP-Referer": settings.web_base_url, "X-Title": "AI Inter-Korean Dialogue"}
    payload = {"model": settings.openrouter_chat_model, "messages": messages, "temperature": 0.4, "max_tokens": 900, "response_format": {"type": "json_object"}}
    async with httpx.AsyncClient(timeout=120) as client:
        last_error = None
        for attempt in range(3):
            try:
                response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    logger.warning("OpenRouter chat retry model=%s attempt=%s status=%s", settings.openrouter_chat_model, attempt + 1, response.status_code)
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                return parse_json_object(content), body.get("usage") or {}
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last_error = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                logger.warning("OpenRouter chat attempt failed model=%s attempt=%s status=%s error_type=%s", settings.openrouter_chat_model, attempt + 1, status, type(exc).__name__)
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"chat response failed: {last_error}")


async def respond(request: AgentRequest) -> dict[str, Any]:
    persona = get_persona(request.agent)
    scenario = get_scenario(request.scenario)
    vector = await embed_query(f"{scenario['title']} {request.opponent_message} {json.dumps(request.negotiation_context, ensure_ascii=False)}")
    candidates = await asyncio.to_thread(search_chunks, vector, 10)
    evidence = select_evidence(candidates, 3)
    messages = build_prompt(persona, scenario, request.relationship_state, request.negotiation_context, request.opponent_message, evidence)
    raw, usage = await chat(messages)
    parsed = AgentResponse.model_validate(raw)
    allowed = {item["id"] for item in evidence}
    invalid = sorted(set(parsed.referenced_evidence_ids) - allowed)
    if invalid:
        raise ValueError(f"invalid evidence IDs: {', '.join(invalid)}")
    return {"agent": {"key": persona.key, "name": persona.name, "side": persona.side, "role": persona.role}, "response": parsed.model_dump(), "evidence": [{key: item[key] for key in ("id", "chunk_id", "document_id", "title", "source_type", "source_url", "similarity", "meeting_date", "content")} for item in evidence], "usage": usage}
