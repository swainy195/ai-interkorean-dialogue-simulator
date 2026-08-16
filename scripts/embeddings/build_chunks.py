"""Build deterministic RAG chunks from the Phase 4 source tables."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path
from statistics import mean
from typing import Any

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "processed" / "chunks"
load_dotenv(ROOT / ".env")

MAX_LEN = 1500
TARGET_LEN = 1200
OVERLAP = 150


def clean(value: Any) -> str:
    return "" if value is None else re.sub(r"[ \t]+", " ", str(value)).strip()


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def metadata(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def paragraphs(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", text) if b.strip()]
    return blocks or ([text.strip()] if text.strip() else [])


def sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    return [part.strip() for part in parts if part.strip()]


def hard_split(text: str, limit: int = MAX_LEN) -> list[str]:
    if len(text) <= limit:
        return [text]
    result = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        result.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - OVERLAP)
    return [part for part in result if part]


def structured_chunks(text: str) -> list[str]:
    blocks = paragraphs(text)
    pieces: list[str] = []
    for block in blocks:
        if len(block) <= MAX_LEN:
            pieces.append(block)
        else:
            sentences = sentence_split(block)
            if len(sentences) == 1:
                pieces.extend(hard_split(block))
            else:
                current = ""
                for sentence in sentences:
                    if len(sentence) > MAX_LEN:
                        if current:
                            pieces.append(current)
                            current = ""
                        pieces.extend(hard_split(sentence))
                    elif current and len(current) + 1 + len(sentence) > TARGET_LEN:
                        pieces.append(current)
                        current = sentence
                    else:
                        current = f"{current} {sentence}".strip()
                if current:
                    pieces.append(current)
    # Pack adjacent short structural blocks while retaining headings and paragraphs.
    packed: list[str] = []
    for piece in pieces:
        if packed and len(packed[-1]) + 2 + len(piece) <= TARGET_LEN:
            packed[-1] += "\n\n" + piece
        else:
            packed.append(piece)
    return packed


def add_chunk(rows: list[dict[str, Any]], doc: dict[str, Any], index: int, content: str) -> None:
    content = content.strip()
    if not content:
        return
    rows.append({
        "document_id": doc["document_id"],
        "source_table": doc["source_table"],
        "source_record_id": doc.get("source_record_id"),
        "chunk_index": index,
        "content": content,
        "title": doc.get("title"),
        "source_type": doc["source_type"],
        "meeting_name": doc.get("meeting_name"),
        "meeting_date": doc.get("meeting_date"),
        "category": doc.get("category"),
        "theme": doc.get("theme"),
        "agenda": doc.get("agenda"),
        "section": doc.get("section"),
        "source_url": doc.get("source_url"),
        "original_filename": doc.get("original_filename"),
        "metadata": doc.get("metadata") or {},
    })


def document_chunks(row: dict[str, Any]) -> list[str]:
    source = row["source_type"]
    if source in {"meeting", "historical_event"}:
        return [row["content"]] if row["content"] else []
    prefix = row.get("prefix", "")
    body = row.get("content", "")
    return structured_chunks(f"{prefix}\n\n{body}".strip())


def fetch_documents(conn: psycopg.Connection) -> dict[str, list[dict[str, Any]]]:
    docs: dict[str, list[dict[str, Any]]] = {"agreements": [], "meeting_documents": [], "meetings": [], "historical_events": []}
    with conn.cursor() as cur:
        cur.execute("select id::text, document_id, title, theme, category, agreement_date, content, source_url, original_filename, source_metadata from public.agreements order by document_id")
        for rid, did, title, theme, category, adate, content, url, filename, source_meta in cur.fetchall():
            docs["agreements"].append({"source_table": "agreements", "source_type": "agreement", "source_record_id": rid, "document_id": did, "title": title, "theme": theme, "category": category, "meeting_date": adate.isoformat() if adate else None, "source_url": url, "original_filename": filename, "metadata": metadata(source_meta), "content": content or "", "prefix": f"제목: {clean(title)}\n회담분야: {clean(theme or category)}\n합의일자: {adate.isoformat() if adate else ''}\n개최국가: {clean((source_meta or {}).get('api_fields', {}).get('country'))}\n지역: {clean((source_meta or {}).get('api_fields', {}).get('region'))}\n시설: {clean((source_meta or {}).get('api_fields', {}).get('facility'))}\n\n본문:"})
        cur.execute("select id::text, document_id, title, meeting_name, document_date, category, content, original_filename, source_url, extraction_method, extraction_warning, source_metadata from public.meeting_documents order by document_id")
        for rid, did, title, meeting_name, ddate, category, content, filename, url, method, warning, source_meta in cur.fetchall():
            docs["meeting_documents"].append({"source_table": "meeting_documents", "source_type": "agreement_commentary", "source_record_id": rid, "document_id": did, "title": title, "meeting_name": meeting_name, "meeting_date": ddate.isoformat() if ddate else None, "category": category, "source_url": url, "original_filename": filename, "metadata": {"extraction_method": method, "warning": warning, **metadata(source_meta)}, "content": content or "", "prefix": f"제목: {clean(title)}\n문서유형: 남북합의서 해설자료\n\n본문:"})
        cur.execute("select id::text, source_meeting_id, meeting_name, meeting_category, meeting_field, start_date, end_date, country, region, facility, summary, source_url, source_metadata from public.meetings order by source_meeting_id")
        for rid, did, name, category, field, start, end, country, region, facility, summary, url, source_meta in cur.fetchall():
            content = f"회담명: {clean(name)}\n분야: {clean(field or category)}\n개최기간: {start.isoformat() if start else ''}~{end.isoformat() if end else ''}\n개최국가: {clean(country)}\n지역: {clean(region)}\n시설: {clean(facility)}\n\n회담내용:\n{clean(summary)}"
            docs["meetings"].append({"source_table": "meetings", "source_type": "meeting", "source_record_id": rid, "document_id": did or f"meeting:{rid}", "title": name, "meeting_name": name, "meeting_date": start.isoformat() if start else None, "category": category, "theme": field, "source_url": url, "metadata": metadata(source_meta), "content": content})
        cur.execute("select id::text, event_id, event_date, title, description, event_type, category, source_url, source_metadata from public.historical_events order by event_id")
        for rid, did, edate, title, description, event_type, category, url, source_meta in cur.fetchall():
            content = f"일자: {edate.isoformat() if edate else ''}\n분류: {clean(category or event_type)}\n사건: {clean(title)}\n내용: {clean(description)}"
            docs["historical_events"].append({"source_table": "historical_events", "source_type": "historical_event", "source_record_id": rid, "document_id": did, "title": title, "meeting_date": edate.isoformat() if edate else None, "category": category or event_type, "source_url": url, "metadata": metadata(source_meta), "content": content})
    return docs


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    stats = []
    with psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20) as conn:
        documents = fetch_documents(conn)
    for table, docs in documents.items():
        rows: list[dict[str, Any]] = []
        for doc in docs:
            for index, content in enumerate(document_chunks(doc)):
                add_chunk(rows, doc, index, content)
        directory = OUT / table
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "chunks.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        lengths = [len(row["content"]) for row in rows]
        keys = [normalize(row["content"]) for row in rows]
        stats.append({"source_type": rows[0]["source_type"] if rows else table, "document_count": len(docs), "chunk_count": len(rows), "min_chunk_length": min(lengths, default=0), "max_chunk_length": max(lengths, default=0), "avg_chunk_length": round(mean(lengths), 2) if lengths else 0, "empty_chunk_count": sum(not row["content"] for row in rows), "too_short_count": sum(0 < n < 250 for n in lengths), "too_long_count": sum(n > MAX_LEN for n in lengths), "duplicate_chunk_count": len(keys) - len(set(keys)), "warning_count": sum((not row.get("title")) or (not row.get("source_url")) for row in rows)})
        all_rows.extend(rows)
    with (OUT / "all_chunks.jsonl").open("w", encoding="utf-8") as handle:
        for row in all_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (OUT / "chunk_manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(stats[0].keys()) if stats else ["source_type"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(stats)
    report = {"documents": sum(s["document_count"] for s in stats), "chunks": len(all_rows), "stats": stats, "empty": sum(s["empty_chunk_count"] for s in stats), "duplicates": sum(s["duplicate_chunk_count"] for s in stats), "too_long": sum(s["too_long_count"] for s in stats)}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
