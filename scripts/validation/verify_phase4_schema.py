from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def main() -> None:
    tables = ["meetings", "agreements", "meeting_documents", "historical_events", "document_chunks"]
    with psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute("select extname from pg_extension where extname in ('vector', 'pgcrypto') order by extname")
            print("EXTENSIONS", [row[0] for row in cur.fetchall()])
            for table in tables:
                cur.execute("select to_regclass(%s)", (f"public.{table}",))
                print("TABLE", table, bool(cur.fetchone()[0]))
            cur.execute("""
                select format_type(a.atttypid, a.atttypmod)
                from pg_attribute a
                join pg_class c on c.oid = a.attrelid
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'public'
                  and c.relname = 'document_chunks'
                  and a.attname = 'embedding'
                  and not a.attisdropped
            """)
            print("EMBEDDING_COLUMN", cur.fetchone()[0])


if __name__ == "__main__":
    main()
