"""Phase 4: collect, normalize, and batch-upsert source data without embeddings."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import httpx
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
API_RAW = RAW / "agreements" / "api"
AGREEMENT_PROCESSED = PROCESSED / "agreements"
MANIFEST_DIR = PROCESSED / "manifests"
API_URL = "https://apis.data.go.kr/1250000/nktalkmng/getNktalkmng"
load_dotenv(ROOT / ".env")


def clean(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def sha(*values: Any) -> str:
    raw = "|".join(clean(value) or "" for value in values)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_date(value: Any) -> tuple[date | None, str | None]:
    raw = clean(value)
    if not raw:
        return None, None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date(), None
        except ValueError:
            pass
    match = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", raw)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))), None
        except ValueError:
            pass
    return None, raw


def first_date(value: Any) -> tuple[date | None, str | None]:
    raw = clean(value)
    if raw and "~" in raw:
        return parse_date(raw.split("~", 1)[0].strip())
    return parse_date(raw)


def read_csv(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            text = raw.decode(encoding)
            return list(csv.DictReader(text.splitlines()))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode {path}")


def jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def batch(values: list[tuple[Any, ...]], size: int = 100) -> Iterable[list[tuple[Any, ...]]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def upsert_many(conn: psycopg.Connection, sql: str, values: list[tuple[Any, ...]], size: int = 100) -> None:
    with conn.cursor() as cur:
        for group in batch(values, size):
            cur.executemany(sql, group)
    conn.commit()


def fetch_agreements() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    API_RAW.mkdir(parents=True, exist_ok=True)
    key = os.environ["DATA_GO_KR_API_KEY"]
    records: list[dict[str, Any]] = []
    total = 0
    pages = 0
    ranges = []
    with httpx.Client(timeout=20.0, headers={"Accept": "application/json"}) as client:
        # The service returns zero for an unfiltered broad range. Its official
        # theme values are used as a finite partition, with the observed
        # country filter required by the live service response.
        start, end = "19900101", "20251231"
        for theme in range(1, 7):
            ranges.append([start, end, str(theme), "북측"])
            page = 1
            fetched_for_partition = 0
            while True:
                params = {"ServiceKey": key, "keyword": "남북", "thema": str(theme), "bgng_ymd": start, "end_ymd": end, "country": "북측", "numOfRows": 100, "pageNo": page}
                response = client.get(API_URL, params=params)
                response.raise_for_status()
                payload = response.json()
                pages += 1
                (API_RAW / f"{start[:4]}_{end[:4]}_theme_{theme}_page_{page:04d}.json").write_bytes(response.content)
                if str(payload.get("resultCode")) not in {"0", "00", "NORMAL_CODE"}:
                    raise RuntimeError(f"agreement API error: {payload.get('resultCode')} {payload.get('resultMsg')} ({start}-{end})")
                items = payload.get("items", [])
                if isinstance(items, dict):
                    items = items.get("item", [])
                if isinstance(items, dict):
                    items = [items]
                records.extend(items)
                fetched_for_partition += len(items)
                year_total = int(payload.get("totalCount") or 0)
                total += year_total if page == 1 else 0
                if fetched_for_partition >= year_total or not items:
                    break
                page += 1
                time.sleep(0.25)
            time.sleep(0.25)
    return records, {"total_count": total, "pages": pages, "date_ranges": ranges, "date_range": ["19900101", "20251231"], "partitions": 6}


def normalize_agreements(records: list[dict[str, Any]]) -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    values = []
    warnings = 0
    seen = set()
    for item in records:
        agreement_date, agreement_date_raw = parse_date(item.get("agmnt_ymd"))
        start_date, start_raw = parse_date(item.get("bgng_ymd"))
        end_date, end_raw = parse_date(item.get("end_ymd"))
        document_id = "agreement:" + sha(item.get("title"), item.get("agmnt_ymd"), item.get("url"), item.get("filenm"))
        if document_id in seen:
            continue
        seen.add(document_id)
        metadata = {"api_fields": item, "raw_dates": {"agmnt_ymd": agreement_date_raw, "bgng_ymd": start_raw, "end_ymd": end_raw}}
        warnings += sum(value is not None for value in (agreement_date_raw, start_raw, end_raw))
        values.append((document_id, clean(item.get("title")), clean(item.get("sj")), clean(item.get("thema")), clean(item.get("catgory")), agreement_date, start_date, end_date, clean(item.get("country")), clean(item.get("region")), clean(item.get("facility")), clean(item.get("cn")), clean(item.get("filenm")), clean(item.get("dwld_url")), clean(item.get("url")), Jsonb(metadata)))
    return values, {"fetched": len(records), "processed": len(values), "duplicates": len(records) - len(values), "date_warnings": warnings}


def build_meetings() -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    main_rows = read_csv(RAW / "통일부_남북회담 정보_20181231.csv")
    held_rows = read_csv(RAW / "통일부_남북관계관리단_개최회담관리_20240920.csv")
    annual_rows = read_csv(RAW / "통일부_남북관계관리단_연도별회담현황데이터관리_20240920.csv")
    merged: dict[str, dict[str, Any]] = {}
    warnings = 0

    def add(key: str, row: dict[str, Any]) -> None:
        nonlocal warnings
        if key not in merged:
            merged[key] = row
        else:
            current = merged[key]
            for field in ("meeting_name", "meeting_field", "start_date", "end_date", "country", "region", "facility", "meeting_count", "visit_count", "summary"):
                if current.get(field) is None and row.get(field) is not None:
                    current[field] = row[field]
            current["source_metadata"]["sources"].extend(row["source_metadata"].get("sources", []))

    for row_number, row in enumerate(main_rows, 1):
        start, start_raw = parse_date(row.get("회담시작일자"))
        end, end_raw = parse_date(row.get("회담종료일자"))
        name = clean(row.get("개최회담")) or clean(row.get("회담명")) or f"unnamed-{row_number}"
        key = "meeting:" + sha(name, start, end)
        warnings += int(start_raw is not None or end_raw is not None)
        add(key, {"source_meeting_id": key, "meeting_name": name, "meeting_category": clean(row.get("회담명")), "meeting_field": clean(row.get("회담분야")), "start_date": start, "end_date": end, "country": clean(row.get("개최국가")), "region": clean(row.get("개최지역")), "facility": clean(row.get("개최시설")), "meeting_count": None, "visit_count": None, "summary": None, "source_metadata": {"sources": [{"file": "통일부_남북회담 정보_20181231.csv", "row": row_number, "raw": row}]}})

    for row_number, row in enumerate(held_rows, 1):
        start, start_raw = parse_date(row.get("회담시작일"))
        end, end_raw = parse_date(row.get("회담종료일"))
        name = clean(row.get("개최회담명")) or f"unnamed-held-{row_number}"
        key = "meeting:" + sha(name, start, end)
        warnings += int(start_raw is not None or end_raw is not None)
        add(key, {"source_meeting_id": key, "meeting_name": name, "meeting_category": None, "meeting_field": None, "start_date": start, "end_date": end, "country": None, "region": None, "facility": None, "meeting_count": int(row["개최회담수"]) if clean(row.get("개최회담수")) and row["개최회담수"].isdigit() else None, "visit_count": int(row["개최방문수"]) if clean(row.get("개최방문수")) and row["개최방문수"].isdigit() else None, "summary": None, "source_metadata": {"sources": [{"file": "통일부_남북관계관리단_개최회담관리_20240920.csv", "row": row_number, "raw": row}]}})

    by_name = defaultdict(list)
    for key, row in merged.items():
        by_name[row["meeting_name"]].append(key)
    for row_number, row in enumerate(annual_rows, 1):
        name = clean(row.get("연도별회담제목")) or f"unnamed-annual-{row_number}"
        matches = by_name.get(name, [])
        if len(matches) == 1:
            merged[matches[0]]["source_metadata"]["sources"].append({"file": "통일부_남북관계관리단_연도별회담현황데이터관리_20240920.csv", "row": row_number, "raw": row})
            if not merged[matches[0]].get("summary"):
                merged[matches[0]]["summary"] = clean(row.get("연도별회담내용"))
        else:
            key = "meeting:" + sha("annual", name, row.get("연도별회담내용"), row.get("작성일"))
            add(key, {"source_meeting_id": key, "meeting_name": name, "meeting_category": None, "meeting_field": None, "start_date": None, "end_date": None, "country": None, "region": None, "facility": None, "meeting_count": None, "visit_count": None, "summary": clean(row.get("연도별회담내용")), "source_metadata": {"sources": [{"file": "통일부_남북관계관리단_연도별회담현황데이터관리_20240920.csv", "row": row_number, "raw": row}], "unmatched_annual_record": True}})
            warnings += 1

    values = []
    for row in merged.values():
        values.append((row["source_meeting_id"], row["meeting_name"], row["meeting_category"], row["meeting_field"], row["start_date"], row["end_date"], row["country"], row["region"], row["facility"], row["meeting_count"], row["visit_count"], row["summary"], "meeting_csv", None, Jsonb(row["source_metadata"])))
    return values, {"source_rows": len(main_rows) + len(held_rows) + len(annual_rows), "main_rows": len(main_rows), "held_rows": len(held_rows), "annual_rows": len(annual_rows), "processed": len(values), "warnings": warnings}


def build_historical_events() -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    rows = read_csv(RAW / "통일부_남북이산가족 연표_20211216.csv")
    values = []
    warnings = 0
    for row_number, row in enumerate(rows, 1):
        event_date, raw_date = parse_date(row.get("날짜"))
        content = clean(row.get("내용")) or ""
        event_id = "historical-event:" + sha(row.get("년대"), row.get("날짜"), content)
        warnings += int(raw_date is not None)
        metadata = {"source_file": "통일부_남북이산가족 연표_20211216.csv", "row": row_number, "raw_date": raw_date, "decade": clean(row.get("년대"))}
        values.append((event_id, event_date, None, content[:200], content, "separated_family", clean(row.get("년대")), "historical_event_csv", None, Jsonb(metadata)))
    return values, {"source_rows": len(rows), "processed": len(values), "date_warnings": warnings}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}, text
    metadata = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip("'\"")
    return metadata, parts[2].lstrip("\r\n")


def build_commentaries() -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    download_rows = {clean(row.get("item_no")): row for row in read_csv(RAW / "agreement_commentaries" / "download_manifest.csv")}
    extraction_rows = read_csv(PROCESSED / "agreement_commentaries" / "extraction_manifest.csv")
    values = []
    warnings = 0
    for row in extraction_rows:
        path = PROCESSED / "agreement_commentaries" / row["processed_filename"]
        text = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        download = download_rows.get(clean(row.get("item_no")), {})
        title = clean(download.get("title")) or clean(frontmatter.get("title")) or Path(row["original_filename"]).stem
        document_id = "commentary:" + (clean(row.get("item_no")) or sha(row.get("original_filename"), row.get("source_url")))
        document_date, date_raw = first_date(download.get("meeting_date"))
        warning = clean(row.get("warning"))
        warnings += int(bool(warning or date_raw))
        metadata = {"download_manifest": download, "extraction_manifest": row, "frontmatter": frontmatter, "raw_date": date_raw}
        values.append((document_id, "agreement_commentary", title, None, None, download.get("meeting_name"), document_date, download.get("category"), body, row.get("original_filename"), row.get("source_url"), row.get("extraction_method"), warning, "meeting_document", Jsonb(metadata)))
    return values, {"source": 83, "processed": len(values), "warnings": warnings, "empty_content": sum(not clean(value[8]) for value in values), "title_missing": sum(not clean(value[2]) for value in values)}


def db_upsert(conn: psycopg.Connection, statements: list[tuple[str, list[tuple[Any, ...]], int]]) -> None:
    for sql, values, size in statements:
        upsert_many(conn, sql, values, size)


def write_agreement_outputs(values: list[tuple[Any, ...]]) -> None:
    AGREEMENT_PROCESSED.mkdir(parents=True, exist_ok=True)
    with (AGREEMENT_PROCESSED / "agreements.jsonl").open("w", encoding="utf-8") as handle:
        for value in values:
            record = {"document_id": value[0], "title": value[1], "subject": value[2], "theme": value[3], "category": value[4], "agreement_date": jsonable(value[5]), "meeting_start_date": jsonable(value[6]), "meeting_end_date": jsonable(value[7]), "country": value[8], "region": value[9], "facility": value[10], "content": value[11], "original_filename": value[12], "download_url": value[13], "source_url": value[14], "source_metadata": value[15].obj}
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    with (AGREEMENT_PROCESSED / "agreement_manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["document_id", "title", "agreement_date", "source_url", "original_filename", "content_empty", "warning"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for value in values:
            writer.writerow({"document_id": value[0], "title": value[1] or "", "agreement_date": jsonable(value[5]) or "", "source_url": value[14] or "", "original_filename": value[12] or "", "content_empty": not bool(clean(value[11]),), "warning": ""})


def write_ingestion_manifest(stats: dict[str, Any]) -> None:
    fields = ["source", "input_count", "processed_count", "inserted_count", "updated_count", "skipped_count", "warning_count", "error_count"]
    rows = [
        {"source": "meetings_csv_3_sources", "input_count": stats["meetings"]["source_rows"], "processed_count": stats["meetings"]["processed"], "inserted_count": "n/a", "updated_count": "n/a", "skipped_count": 0, "warning_count": stats["meetings"]["warnings"], "error_count": 0},
        {"source": "agreements_api", "input_count": stats["agreements"]["fetched"], "processed_count": stats["agreements"]["processed"], "inserted_count": "n/a", "updated_count": "n/a", "skipped_count": stats["agreements"]["duplicates"], "warning_count": stats["agreements"]["date_warnings"], "error_count": 0},
        {"source": "agreement_commentaries", "input_count": stats["agreement_commentaries"]["source"], "processed_count": stats["agreement_commentaries"]["processed"], "inserted_count": "n/a", "updated_count": "n/a", "skipped_count": 0, "warning_count": stats["agreement_commentaries"]["warnings"], "error_count": 0},
        {"source": "historical_events_csv", "input_count": stats["historical_events"]["source_rows"], "processed_count": stats["historical_events"]["processed"], "inserted_count": "n/a", "updated_count": "n/a", "skipped_count": 0, "warning_count": stats["historical_events"]["date_warnings"], "error_count": 0},
    ]
    with (MANIFEST_DIR / "phase4_ingestion_manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def count(conn: psycopg.Connection, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"select count(*) from public.{table}")
        return int(cur.fetchone()[0])


def main() -> None:
    for directory in (API_RAW, AGREEMENT_PROCESSED, MANIFEST_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    api_records, api_info = fetch_agreements()
    agreement_values, agreement_stats = normalize_agreements(api_records)
    write_agreement_outputs(agreement_values)
    meeting_values, meeting_stats = build_meetings()
    event_values, event_stats = build_historical_events()
    commentary_values, commentary_stats = build_commentaries()

    agreement_sql = """insert into public.agreements (document_id,title,subject,theme,category,agreement_date,meeting_start_date,meeting_end_date,country,region,facility,content,original_filename,download_url,source_url,source_metadata) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (document_id) do update set title=excluded.title,subject=excluded.subject,theme=excluded.theme,category=excluded.category,agreement_date=excluded.agreement_date,meeting_start_date=excluded.meeting_start_date,meeting_end_date=excluded.meeting_end_date,country=excluded.country,region=excluded.region,facility=excluded.facility,content=excluded.content,original_filename=excluded.original_filename,download_url=excluded.download_url,source_url=excluded.source_url,source_metadata=excluded.source_metadata,updated_at=now()"""
    meeting_sql = """insert into public.meetings (source_meeting_id,meeting_name,meeting_category,meeting_field,start_date,end_date,country,region,facility,meeting_count,visit_count,summary,source_type,source_url,source_metadata) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (source_meeting_id) where source_meeting_id is not null do update set meeting_name=excluded.meeting_name,meeting_category=excluded.meeting_category,meeting_field=excluded.meeting_field,start_date=excluded.start_date,end_date=excluded.end_date,country=excluded.country,region=excluded.region,facility=excluded.facility,meeting_count=excluded.meeting_count,visit_count=excluded.visit_count,summary=excluded.summary,source_metadata=excluded.source_metadata,updated_at=now()"""
    event_sql = """insert into public.historical_events (event_id,event_date,end_date,title,description,event_type,category,source_type,source_url,source_metadata) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (event_id) do update set event_date=excluded.event_date,title=excluded.title,description=excluded.description,event_type=excluded.event_type,category=excluded.category,source_metadata=excluded.source_metadata,updated_at=now()"""
    commentary_sql = """insert into public.meeting_documents (document_id,document_type,title,meeting_id,agreement_id,meeting_name,document_date,category,content,original_filename,source_url,extraction_method,extraction_warning,source_type,source_metadata) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (document_id) do update set document_type=excluded.document_type,title=excluded.title,meeting_name=excluded.meeting_name,document_date=excluded.document_date,category=excluded.category,content=excluded.content,original_filename=excluded.original_filename,source_url=excluded.source_url,extraction_method=excluded.extraction_method,extraction_warning=excluded.extraction_warning,source_metadata=excluded.source_metadata,updated_at=now()"""

    with psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20) as conn:
        db_upsert(conn, [(meeting_sql, meeting_values, 100), (agreement_sql, agreement_values, 50), (event_sql, event_values, 100), (commentary_sql, commentary_values, 25)])
        counts = {table: count(conn, table) for table in ("meetings", "agreements", "meeting_documents", "historical_events", "document_chunks")}

    report = {"meetings": meeting_stats | {"db_rows": counts["meetings"]}, "agreements": api_info | agreement_stats | {"db_rows": counts["agreements"], "empty_content": sum(not clean(value[11]) for value in agreement_values), "title_missing": sum(not clean(value[1]) for value in agreement_values), "source_url_missing": sum(not clean(value[14]) for value in agreement_values)}, "agreement_commentaries": commentary_stats | {"db_rows": counts["meeting_documents"]}, "historical_events": event_stats | {"db_rows": counts["historical_events"]}, "final_counts": counts}
    write_ingestion_manifest(report)
    (MANIFEST_DIR / "phase4_ingestion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=jsonable), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=jsonable))


if __name__ == "__main__":
    main()
