from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def sample(cur, table: str, columns: str) -> None:
    cur.execute(f"select {columns} from public.{table} order by created_at limit 3")
    print("SAMPLE", table)
    for row in cur.fetchall():
        print(row)


def main() -> None:
    with psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for table in ("meetings", "agreements", "meeting_documents", "historical_events", "document_chunks"):
                cur.execute(f"select count(*) from public.{table}")
                print("COUNT", table, cur.fetchone()[0])
            checks = {
                "agreements_duplicate_document_id": "select count(*) - count(distinct document_id) from public.agreements",
                "meeting_documents_duplicate_document_id": "select count(*) - count(distinct document_id) from public.meeting_documents",
                "historical_duplicate_event_id": "select count(*) - count(distinct event_id) from public.historical_events",
                "agreements_null_title": "select count(*) from public.agreements where title is null or btrim(title) = ''",
                "agreements_empty_content": "select count(*) from public.agreements where content is null or btrim(content) = ''",
                "agreements_missing_source_url": "select count(*) from public.agreements where source_url is null or btrim(source_url) = ''",
                "commentary_null_title": "select count(*) from public.meeting_documents where title is null or btrim(title) = ''",
                "commentary_empty_content": "select count(*) from public.meeting_documents where content is null or btrim(content) = ''",
                "commentary_missing_source_url": "select count(*) from public.meeting_documents where source_url is null or btrim(source_url) = ''",
                "historical_date_null": "select count(*) from public.historical_events where event_date is null",
                "chunks_count": "select count(*) from public.document_chunks",
            }
            for name, query in checks.items():
                cur.execute(query)
                print("QUALITY", name, cur.fetchone()[0])
            sample(cur, "meetings", "meeting_name, start_date, end_date, source_metadata")
            sample(cur, "agreements", "title, agreement_date, content, source_url, source_metadata")
            sample(cur, "meeting_documents", "title, document_date, content, source_url, source_metadata")
            sample(cur, "historical_events", "title, event_date, description, source_metadata")


if __name__ == "__main__":
    main()
