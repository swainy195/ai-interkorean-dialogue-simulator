"""Batch upsert validated Phase 5 chunks and vectors into Supabase PostgreSQL."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / "data" / "processed" / "chunks" / "embedded_chunks.jsonl"
load_dotenv(ROOT / ".env")


def groups(values: list[tuple[Any, ...]], size: int) -> Iterable[list[tuple[Any, ...]]]:
    for start in range(0, len(values), size):
        yield values[start:start + size]


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def main() -> None:
    rows = [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines() if line.strip()]
    values = []
    for row in rows:
        vector = row.get("embedding")
        if not isinstance(vector, list) or len(vector) != 2048:
            raise ValueError(f"invalid embedding for {row.get('document_id')}:{row.get('chunk_index')}")
        values.append((row["document_id"], row["source_table"], row.get("source_record_id"), row["chunk_index"], row["content"], row.get("title"), row.get("source_type"), row.get("meeting_name"), row.get("meeting_date"), row.get("category"), row.get("theme"), row.get("agenda"), row.get("section"), row.get("source_url"), row.get("original_filename"), Jsonb(row.get("metadata") or {}), row.get("embedding_model"), vector_literal(vector)))
    sql = """insert into public.document_chunks (document_id,source_table,source_record_id,chunk_index,content,title,source_type,meeting_name,meeting_date,category,theme,agenda,section,source_url,original_filename,metadata,embedding_model,embedding) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector) on conflict (document_id,chunk_index) do update set source_table=excluded.source_table,source_record_id=excluded.source_record_id,content=excluded.content,title=excluded.title,source_type=excluded.source_type,meeting_name=excluded.meeting_name,meeting_date=excluded.meeting_date,category=excluded.category,theme=excluded.theme,agenda=excluded.agenda,section=excluded.section,source_url=excluded.source_url,original_filename=excluded.original_filename,metadata=excluded.metadata,embedding_model=excluded.embedding_model,embedding=excluded.embedding"""
    with psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for group in groups(values, 100):
                cur.executemany(sql, group)
            current_keys = {(row[0], row[3]) for row in values}
            cur.execute("select document_id, chunk_index from public.document_chunks")
            stale = [key for key in cur.fetchall() if key not in current_keys]
            cur.executemany("delete from public.document_chunks where document_id=%s and chunk_index=%s", stale)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("select count(*) from public.document_chunks")
            total = cur.fetchone()[0]
            cur.execute("select count(*) from public.document_chunks where embedding is null")
            nulls = cur.fetchone()[0]
            cur.execute("select source_type, count(*) from public.document_chunks group by source_type order by source_type")
            by_source = dict(cur.fetchall())
    report = {"input_rows": len(rows), "stale_removed": len(stale), "document_chunks": total, "embedding_null": nulls, "source_type_counts": by_source}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if total != len(rows) or nulls:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
