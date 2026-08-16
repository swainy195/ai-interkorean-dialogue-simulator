from __future__ import annotations

import os
from typing import Any

import psycopg

from app.config import get_settings


def search_chunks(vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
    literal = "[" + ",".join(str(float(value)) for value in vector) + "]"
    with psycopg.connect(get_settings().supabase_db_url, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute("select id, document_id, content, title, source_type, source_url, metadata, similarity from public.match_document_chunks(%s::vector, %s, %s, %s)", (literal, limit, None, None))
            return [{"id": str(row[0]), "document_id": row[1], "content": row[2], "title": row[3], "source_type": row[4], "source_url": row[5], "metadata": row[6] or {}, "similarity": float(row[7])} for row in cur.fetchall()]
