from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_csv(path: Path):
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.DictReader(text.splitlines()))
    return encoding, list(rows[0].keys()) if rows else [], rows


def main() -> None:
    for path in sorted((ROOT / "data" / "raw").glob("*.csv")):
        encoding, columns, rows = read_csv(path)
        nulls = {column: sum(not (row.get(column) or "").strip() for row in rows) for column in columns}
        duplicate_rows = len(rows) - len({tuple((row.get(column) or "").strip() for column in columns) for row in rows})
        candidates = []
        for column in columns:
            values = [(row.get(column) or "").strip() for row in rows]
            nonempty = [value for value in values if value]
            if nonempty and len(set(nonempty)) == len(nonempty):
                candidates.append(column)
        date_like = {}
        for column in columns:
            values = [((row.get(column) or "").strip()) for row in rows if (row.get(column) or "").strip()]
            if values:
                date_like[column] = sum(any(token in value for token in ("년", "월", "일", "-", "/", ".")) or (len(value) == 8 and value.isdigit()) for value in values)
        print(json.dumps({"file": path.name, "encoding": encoding, "rows": len(rows), "columns": len(columns), "column_names": columns, "null_count": nulls, "unique_candidate_keys": candidates, "date_like_counts": date_like, "duplicate_rows": duplicate_rows, "sample_3": rows[:3]}, ensure_ascii=False, indent=2))

    raw_manifest = ROOT / "data" / "raw" / "agreement_commentaries" / "download_manifest.csv"
    processed_manifest = ROOT / "data" / "processed" / "agreement_commentaries" / "extraction_manifest.csv"
    for path in (raw_manifest, processed_manifest):
        encoding, columns, rows = read_csv(path)
        print(json.dumps({"file": str(path.relative_to(ROOT)), "encoding": encoding, "rows": len(rows), "columns": len(columns), "column_names": columns, "sample_3": rows[:3]}, ensure_ascii=False, indent=2))

    markdowns = sorted((ROOT / "data" / "processed" / "agreement_commentaries").glob("*.md"))
    print(json.dumps({"markdown_count": len(markdowns), "raw_file_count": len(list((ROOT / "data" / "raw" / "agreement_commentaries").glob("*.hwp"))) + len(list((ROOT / "data" / "raw" / "agreement_commentaries").glob("*.pdf")))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
