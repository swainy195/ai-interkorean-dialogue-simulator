"""Validate generated Phase 5 chunk JSONL without changing source data."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "data" / "processed" / "chunks" / "all_chunks.jsonl"
REQUIRED = ("document_id", "source_table", "chunk_index", "content", "title", "source_type", "metadata")


def main() -> None:
    rows = [json.loads(line) for line in PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    duplicate_content = len(rows) - len({" ".join(row["content"].split()) for row in rows})
    duplicate_keys = len(rows) - len({(row["document_id"], row["chunk_index"]) for row in rows})
    missing = {field: sum(row.get(field) in (None, "") for row in rows) for field in REQUIRED}
    report = {
        "chunks": len(rows),
        "empty": sum(not row.get("content", "").strip() for row in rows),
        "too_short_under_250": sum(0 < len(row.get("content", "")) < 250 for row in rows),
        "too_long_over_1500": sum(len(row.get("content", "")) > 1500 for row in rows),
        "duplicate_content": duplicate_content,
        "duplicate_document_chunk_index": duplicate_keys,
        "replacement_character": sum("\ufffd" in row.get("content", "") for row in rows),
        "missing_required": missing,
        "missing_source_url": sum(not row.get("source_url") for row in rows),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["empty"] or report["too_long_over_1500"] or report["duplicate_document_chunk_index"] or report["replacement_character"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
