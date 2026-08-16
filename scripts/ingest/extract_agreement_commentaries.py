"""Extract agreement commentary originals into UTF-8 Markdown with QA metadata."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader
from playwright.sync_api import sync_playwright


RAW_DIR = Path("data/raw/agreement_commentaries")
PROCESSED_DIR = Path("data/processed/agreement_commentaries")
SOURCE_MANIFEST = RAW_DIR / "download_manifest.csv"
OUTPUT_MANIFEST = PROCESSED_DIR / "extraction_manifest.csv"
OUTPUT_FIELDS = [
    "item_no",
    "original_filename",
    "processed_filename",
    "source_url",
    "file_type",
    "file_size",
    "extraction_method",
    "extraction_status",
    "character_count",
    "korean_character_ratio",
    "title_detected",
    "warning",
    "error",
]
HANGUL_RE = re.compile(r"[가-힣]")
REPLACEMENT_RE = re.compile("\ufffd")
SHORT_CHARACTER_THRESHOLD = 100
LOW_KOREAN_RATIO_THRESHOLD = 0.05


def yaml_value(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Keep paragraph and heading boundaries, while removing converter noise.
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    cleaned: list[str] = []
    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            if blank_count <= 2:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def extract_pdf(path: Path) -> tuple[str, str]:
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = clean_text(page_text)
        if page_text:
            pages.append(f"<!-- Page {page_number} -->\n\n{page_text}")
    return "\n\n".join(pages), "pypdf"


def extract_hwp(path: Path, hwp5txt: str) -> tuple[str, str]:
    result = subprocess.run(
        [hwp5txt, str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise RuntimeError(detail[-1] if detail else f"hwp5txt exited with {result.returncode}")
    return clean_text(result.stdout), "pyhwp-hwp5txt"


def extract_hwp_preview(page, source_url: str, delay: float) -> tuple[str, str]:
    """Use the site's public HTML preview conversion for legacy HWP V3 files."""
    preview_url = source_url.replace("/common/download.do", "/common/htmlPreView.do")
    if preview_url == source_url:
        raise RuntimeError("source URL has no HTML preview endpoint")
    page.goto(preview_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(max(0, int(delay * 1000)))
    candidates: list[str] = []
    for frame in page.frames:
        try:
            value = frame.locator("body").inner_text(timeout=10000)
        except Exception:
            continue
        value = clean_text(value.replace("\xa0", " "))
        if len(value) > 100:
            candidates.append(value)
    if not candidates:
        raise RuntimeError("official HTML preview contained no extractable body text")
    return max(candidates, key=len), "official-html-preview"


def character_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def korean_ratio(text: str) -> float:
    denominator = character_count(text)
    return round(len(HANGUL_RE.findall(text)) / denominator, 4) if denominator else 0.0


def title_is_detected(text: str, title: str) -> bool:
    if not text:
        return False
    first_lines = "\n".join(line for line in text.splitlines() if line.strip())[:2000]
    normalized_title = re.sub(r"\s+", "", title or "")
    normalized_head = re.sub(r"\s+", "", first_lines)
    if normalized_title and normalized_title in normalized_head:
        return True
    # A title-like first line is useful when the site title and document title differ.
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return 4 <= len(first_line) <= 160 and not first_line.endswith((".", ",", ";"))


def quality_warnings(text: str, title: str) -> list[str]:
    warnings: list[str] = []
    count = character_count(text)
    ratio = korean_ratio(text)
    if count == 0:
        warnings.append("empty document")
    elif count < SHORT_CHARACTER_THRESHOLD:
        warnings.append(f"short document ({count} characters)")
    if count and ratio < LOW_KOREAN_RATIO_THRESHOLD:
        warnings.append(f"low Korean character ratio ({ratio:.4f})")
    if REPLACEMENT_RE.search(text):
        warnings.append("replacement character U+FFFD detected")
    if not title_is_detected(text, title):
        warnings.append("title not detected")
    return warnings


def write_markdown(path: Path, metadata: dict[str, str], text: str, error: str | None) -> None:
    lines = ["---"]
    for key in ("source_type", "original_filename", "source_url", "item_no", "category", "meeting_name", "meeting_date", "extraction_method", "extraction_status"):
        lines.append(f"{key}: {yaml_value(metadata.get(key, ''))}")
    lines.extend(["---", ""])
    if error:
        lines.extend(["> Text extraction failed; the original file is preserved unchanged.", "", f"Extraction error: {error}", ""])
    if text:
        lines.extend([text, ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def read_source_rows() -> list[dict[str, str]]:
    with SOURCE_MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_manifest(rows: Iterable[dict[str, str]]) -> None:
    with OUTPUT_MANIFEST.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def preview(text: str, limit: int = 500) -> str:
    compact = re.sub(r"\n{3,}", "\n\n", text).strip()
    return compact[:limit] + ("…" if len(compact) > limit else "")


def run(preview_delay: float = 1.5) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    hwp5txt = shutil.which("hwp5txt")
    if not hwp5txt:
        raise RuntimeError("hwp5txt executable was not found; install pyhwp first")

    rows: list[dict[str, str]] = []
    samples: list[tuple[dict[str, str], Path, str]] = []
    browser_runtime = sync_playwright().start()
    preview_browser = browser_runtime.chromium.launch(headless=True)
    preview_context = preview_browser.new_context()
    preview_page = preview_context.new_page()
    try:
      for source in read_source_rows():
        if source.get("download_status") not in {"downloaded", "already_exists"}:
            continue
        raw_path = Path(source["local_path"])
        processed_path = PROCESSED_DIR / f"{raw_path.stem}.md"
        file_type = raw_path.suffix.lower().lstrip(".")
        text = ""
        method = ""
        status = "failed"
        error = ""
        warnings: list[str] = []
        try:
            if not raw_path.exists():
                raise FileNotFoundError(str(raw_path))
            if file_type == "pdf":
                text, method = extract_pdf(raw_path)
            elif file_type == "hwp":
                try:
                    text, method = extract_hwp(raw_path, hwp5txt)
                except Exception as parser_exc:
                    try:
                        text, method = extract_hwp_preview(preview_page, source.get("source_url", ""), preview_delay)
                    except Exception as preview_exc:
                        raise RuntimeError(f"hwp5txt: {parser_exc}; html preview: {preview_exc}") from preview_exc
            else:
                raise RuntimeError(f"unsupported file type: {file_type}")
            warnings = quality_warnings(text, source.get("title", ""))
            status = "warning" if warnings else "success"
        except Exception as exc:  # one bad document must not stop the batch
            method = "pypdf" if file_type == "pdf" else "pyhwp-hwp5txt" if file_type == "hwp" else ""
            error = f"{type(exc).__name__}: {exc}"
        metadata = {
            "source_type": "agreement_commentary",
            "original_filename": source.get("original_filename", ""),
            "source_url": source.get("source_url", ""),
            "item_no": source.get("item_no", ""),
            "category": source.get("category", ""),
            "meeting_name": source.get("meeting_name", ""),
            "meeting_date": source.get("meeting_date", ""),
            "extraction_method": method,
            "extraction_status": status,
        }
        write_markdown(processed_path, metadata, text, error or None)
        rows.append({
            "item_no": source.get("item_no", ""),
            "original_filename": source.get("original_filename", ""),
            "processed_filename": processed_path.name,
            "source_url": source.get("source_url", ""),
            "file_type": file_type,
            "file_size": str(raw_path.stat().st_size) if raw_path.exists() else "",
            "extraction_method": method,
            "extraction_status": status,
            "character_count": str(character_count(text)),
            "korean_character_ratio": f"{korean_ratio(text):.4f}",
            "title_detected": str(title_is_detected(text, source.get("title", ""))).lower(),
            "warning": "; ".join(warnings),
            "error": error,
        })
        samples.append((source, processed_path, text))
    finally:
        preview_context.close()
        preview_browser.close()
        browser_runtime.stop()

    write_manifest(rows)
    counts = Counter(row["extraction_status"] for row in rows)
    successful = [row for row in rows if row["extraction_status"] in {"success", "warning"}]
    lengths = [int(row["character_count"]) for row in successful]
    warning_rows = [row for row in rows if row["extraction_status"] == "warning"]
    sorted_samples = sorted(samples, key=lambda item: len(re.sub(r"\s+", "", item[2])))
    selected: list[tuple[dict[str, str], Path, str]] = []
    selected.extend(sorted_samples[:2])
    selected.extend(sorted_samples[-2:])
    selected.extend(random.Random(42).sample(samples, min(3, len(samples))))
    print("텍스트 추출 결과")
    print(f"전체 원본: {len(rows)}")
    print(f"HWP: {sum(row['file_type'] == 'hwp' for row in rows)}")
    print(f"PDF: {sum(row['file_type'] == 'pdf' for row in rows)}")
    print(f"추출 성공: {counts['success']}")
    print(f"경고: {counts['warning']}")
    print(f"실패: {counts['failed']}")
    print(f"Markdown 생성 수: {len(rows)}")
    print(f"평균 문자 수: {sum(lengths) / len(lengths) if lengths else 0:.1f}")
    print(f"최소 문자 수: {min(lengths) if lengths else 0}")
    print(f"최대 문자 수: {max(lengths) if lengths else 0}")
    print(f"깨진 문자 발견: {sum('replacement character' in row['warning'] for row in rows)}")
    print(f"빈 문서: {sum('empty document' in row['warning'] for row in rows)}")
    print(f"비정상적으로 짧은 문서: {sum('short document' in row['warning'] for row in rows)}")
    print(f"Manifest: {OUTPUT_MANIFEST.as_posix()}")
    print("검수 샘플:")
    seen: set[str] = set()
    for source, path, text in selected:
        if path.name in seen:
            continue
        seen.add(path.name)
        print(f"- {path.as_posix()} | item_no={source.get('item_no', '')}")
        print(preview(text).replace("\n", " ") or "(추출 텍스트 없음)")
    print("검수 필요 파일:")
    for row in warning_rows[:5]:
        print(f"- {row['original_filename']} / {row['warning']}")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-delay", type=float, default=1.5)
    args = parser.parse_args()
    raise SystemExit(run(args.preview_delay))
