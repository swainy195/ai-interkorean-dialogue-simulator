"""Run Korean retrieval smoke tests through OpenRouter embeddings + pgvector."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
QUERIES = [
    "이산가족 상봉 재개와 관련된 과거 합의와 회담은 무엇인가?",
    "남북 철도와 도로 연결을 위한 공동조사 및 협력 사례",
    "군사적 긴장완화와 우발적 충돌 방지를 위한 남북 합의",
    "남북 고위급 회담에서 주요하게 논의된 내용",
]


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def embed(client: httpx.Client, text: str) -> list[float]:
    for attempt in range(3):
        try:
            response = client.post("https://openrouter.ai/api/v1/embeddings", json={"model": os.environ["OPENROUTER_EMBEDDING_MODEL"], "input": text})
            response.raise_for_status()
            vector = (response.json().get("data") or [])[0].get("embedding")
            if not isinstance(vector, list) or len(vector) != 2048:
                raise RuntimeError("invalid query vector")
            return vector
        except (httpx.HTTPError, ValueError, IndexError, RuntimeError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"}
    results = []
    with httpx.Client(timeout=90, headers=headers) as client, psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20) as conn:
        for query in QUERIES:
            vector = vector_literal(embed(client, query))
            with conn.cursor() as cur:
                cur.execute("select id, document_id, content, title, source_type, source_url, metadata, similarity from public.match_document_chunks(%s::vector, %s, %s, %s)", (vector, 10, None, None))
                rows = cur.fetchall()
            results.append({"query": query, "top10": [{"rank": index, "document_id": row[1], "title": row[3], "source_type": row[4], "similarity": round(float(row[7]), 6), "content_preview": row[2][:180].replace("\n", " ")} for index, row in enumerate(rows, 1)]})
    print(json.dumps({"model": os.environ["OPENROUTER_EMBEDDING_MODEL"], "dimension": 2048, "queries": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
