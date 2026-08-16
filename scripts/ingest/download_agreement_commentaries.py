"""Collect attachments from the Ministry of Unification agreement commentary list.

The script intentionally uses Playwright for both navigation and attachment
retrieval. It does not attempt to bypass login, CAPTCHA, robots restrictions,
or other access controls.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from playwright.async_api import BrowserContext, Page, Response, async_playwright


LIST_URL = "https://dialogue.unikorea.go.kr/ukd/c/cc/usrtalkmanage/List.do?tab=6"
OUTPUT_DIR = Path("data/raw/agreement_commentaries")
MANIFEST_PATH = OUTPUT_DIR / "download_manifest.csv"
MANIFEST_FIELDS = [
    "item_no",
    "category",
    "title",
    "meeting_name",
    "meeting_date",
    "original_filename",
    "local_path",
    "source_url",
    "attachment_id",
    "download_status",
    "error",
]
ALLOWED_EXTENSIONS = {".hwp", ".hwpx", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}
FILE_MIME_HINTS = (
    "application/pdf",
    "application/octet-stream",
    "application/zip",
    "application/vnd.",
    "application/msword",
)


@dataclass
class Item:
    item_no: str
    category: str
    title: str
    meeting_name: str
    meeting_date: str
    attachment_urls: list[str]


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def safe_filename(filename: str) -> str:
    filename = unquote(filename).replace("\\", "_").replace("/", "_")
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', "_", filename).strip(" .")
    return filename or "attachment.bin"


def attachment_id_from_url(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    for key in ("id", "fileId", "atchFileId", "attachmentId"):
        if query.get(key):
            return query[key][0]
    match = re.search(r"(?:id|file)[=/]([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else ""


def filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"filename\*=UTF-8''([^;]+)", value, re.I)
    if match:
        return unquote(match.group(1).strip('"'))
    match = re.search(r'filename="?([^";]+)', value, re.I)
    return unquote(match.group(1).strip()) if match else None


def filename_from_url(url: str) -> str | None:
    name = Path(unquote(urlparse(url).path)).name
    return name if "." in name else None


def is_file_response(response: Response) -> bool:
    content_type = (response.headers.get("content-type") or "").lower()
    disposition = (response.headers.get("content-disposition") or "").lower()
    path = urlparse(response.url).path.lower()
    return (
        "attachment" in disposition
        or any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)
        or any(hint in content_type for hint in FILE_MIME_HINTS)
    ) and "text/html" not in content_type


def validate_file(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return "file is missing or empty"
    data = path.read_bytes()[:32]
    ext = path.suffix.lower()
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        return "extension is .pdf but the file signature is not PDF"
    if ext == ".hwp" and data != b"" and not (
        data.startswith(b"\xd0\xcf\x11\xe0")
        or data.startswith(b"HWP Document File")
    ):
        return "extension is .hwp but the file signature is not a recognized HWP file"
    if ext == ".hwpx" and not data.startswith(b"PK"):
        return "extension is .hwpx but the file signature is not a ZIP package"
    if ext not in ALLOWED_EXTENSIONS:
        return f"unsupported attachment extension: {ext or '(none)'}"
    return None


async def polite_pause(delay: float) -> None:
    await asyncio.sleep(max(0.0, delay))


async def check_robots(context: BrowserContext, target_url: str) -> None:
    robots_url = urljoin(target_url, "/robots.txt")
    response = await context.request.get(robots_url, fail_on_status_code=False)
    if response.status == 404:
        return
    if not response.ok:
        raise RuntimeError(f"robots.txt could not be read (HTTP {response.status}); refusing to crawl")
    body = (await response.text()).splitlines()
    user_agent = "*"
    applies = False
    disallowed: list[str] = []
    for raw_line in body:
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (part.strip().lower() for part in line.split(":", 1))
        if key == "user-agent":
            applies = value == user_agent
        elif applies and key == "disallow" and value:
            disallowed.append(value)
    path = urlparse(target_url).path
    if any(path.startswith(rule) for rule in disallowed):
        raise RuntimeError(f"robots.txt disallows the target path: {path}")


async def extract_items(page: Page) -> list[Item]:
    tables = page.locator("table")
    for table_index in range(await tables.count()):
        table = tables.nth(table_index)
        header = clean_text(await table.locator("tr").first.inner_text())
        if "번호" not in header or "첨부파일" not in header:
            continue
        rows = table.locator("tr")
        items: list[Item] = []
        for row_index in range(1, await rows.count()):
            row = rows.nth(row_index)
            cells = row.locator("th, td")
            values = [clean_text(await cells.nth(i).inner_text()) for i in range(await cells.count())]
            if len(values) < 5 or not re.fullmatch(r"\d+", values[0]):
                continue
            direct_download_urls: list[str] = []
            preview_urls: list[str] = []
            attachment_cell = cells.nth(len(values) - 1)
            for link_index in range(await attachment_cell.locator("a").count()):
                link = attachment_cell.locator("a").nth(link_index)
                href = await link.get_attribute("href")
                if not href:
                    continue
                absolute = urljoin(page.url, href)
                text = clean_text(await link.inner_text())
                title = clean_text(await link.get_attribute("title"))
                if "/common/download.do" in absolute.lower() or "download" in title.lower():
                    direct_download_urls.append(absolute)
                elif text:
                    preview_urls.append(absolute)
            attachment_urls = direct_download_urls or preview_urls
            items.append(Item(values[0], values[1], values[2], values[3], values[4], attachment_urls))
        return items
    raise RuntimeError("the agreement commentary table was not found")


async def go_to_page(page: Page, page_number: int, delay: float) -> None:
    if page_number == 1:
        await page.goto(LIST_URL, wait_until="domcontentloaded")
        await polite_pause(delay)
        return
    page_offset = (page_number - 1) * 10 + 1
    # The site uses jsMovePage(offset) for both numbered links and the
    # next-page-group control. Calling the same public page function avoids
    # depending on whether the current page is rendered as an <a> or a label.
    await page.evaluate("offset => jsMovePage(offset)", page_offset)
    await page.wait_for_timeout(5000)
    await polite_pause(delay)


async def total_pages_from(page: Page) -> int:
    body = await page.locator("body").inner_text()
    match = re.search(r"페이지\s*:\s*\d+\s*/\s*(\d+)", body)
    if not match:
        raise RuntimeError("total page count was not found on the list page")
    return int(match.group(1))


async def current_page_from(page: Page) -> int | None:
    body = await page.locator("body").inner_text()
    match = re.search(r"페이지\s*:\s*(\d+)\s*/\s*\d+", body)
    return int(match.group(1)) if match else None


async def discover_file(page: Page, source_url: str, delay: float) -> tuple[str, bytes, str]:
    """Return (filename, bytes, response_url) from a preview/download page."""
    # The list exposes a direct /common/download.do endpoint. Use the
    # Playwright request context so its cookies/session are retained, while
    # avoiding the slower HTML preview conversion path.
    direct_response = await page.request.get(source_url, fail_on_status_code=False)
    direct_content_type = (direct_response.headers.get("content-type") or "").lower()
    direct_disposition = direct_response.headers.get("content-disposition")
    if direct_response.ok and (
        "attachment" in (direct_disposition or "").lower()
        or "text/html" not in direct_content_type
    ):
        body = await direct_response.body()
        filename = (
            filename_from_content_disposition(direct_disposition)
            or filename_from_url(direct_response.url)
            or f"attachment_{attachment_id_from_url(source_url)}.bin"
        )
        return safe_filename(filename), body, direct_response.url

    file_responses: list[Response] = []

    async def record_response(response: Response) -> None:
        if is_file_response(response):
            file_responses.append(response)

    page.on("response", record_response)
    await page.goto(source_url, wait_until="domcontentloaded")
    await polite_pause(delay)

    # Some preview pages expose a second link for the actual content.
    links = page.locator("a")
    candidates: list[tuple[str, str]] = []
    for i in range(await links.count()):
        link = links.nth(i)
        href = await link.get_attribute("href")
        if not href or href.lower().startswith("javascript:"):
            continue
        absolute = urljoin(page.url, href)
        text = clean_text(await link.inner_text())
        if any(token in (absolute + " " + text).lower() for token in ("download", "file", "content", ".hwp", ".pdf", ".hwpx")):
            candidates.append((absolute, text))
    for href, _ in candidates:
        try:
            await page.goto(href, wait_until="domcontentloaded")
            await polite_pause(delay)
        except Exception:
            continue
        if file_responses:
            break

    if not file_responses:
        raise RuntimeError("no downloadable file response was found in the attachment preview")
    response = file_responses[-1]
    body = await response.body()
    filename = (
        filename_from_content_disposition(response.headers.get("content-disposition"))
        or filename_from_url(response.url)
        or filename_from_url(source_url)
        or "attachment.bin"
    )
    return safe_filename(filename), body, response.url


def write_manifest(rows: Iterable[dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def load_existing_manifest() -> dict[str, dict[str, str]]:
    """Index prior successful rows so a rerun can skip the network request."""
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        prior_rows = csv.DictReader(handle)
        indexed: dict[str, dict[str, str]] = {}
        for row in prior_rows:
            if row.get("download_status") not in {"downloaded", "already_exists"}:
                continue
            local_path = Path(row.get("local_path") or "")
            if not local_path.exists():
                continue
            for key in (row.get("attachment_id", ""), row.get("source_url", "")):
                if key:
                    indexed[key] = row
        return indexed


async def run(delay: float, headed: bool) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing_manifest = load_existing_manifest()
    rows: list[dict[str, str]] = []
    total_items = attachment_items = downloaded = existing = failures = 0
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not headed)
        context = await browser.new_context(accept_downloads=True)
        try:
            await check_robots(context, LIST_URL)
            page = await context.new_page()
            await go_to_page(page, 1, delay)
            total_pages = await total_pages_from(page)
            for page_number in range(1, total_pages + 1):
                if page_number > 1:
                    await go_to_page(page, page_number, delay)
                items = await extract_items(page)
                total_items += len(items)
                for item in items:
                    if not item.attachment_urls:
                        rows.append({
                            "item_no": item.item_no, "category": item.category, "title": item.title,
                            "meeting_name": item.meeting_name, "meeting_date": item.meeting_date,
                            "original_filename": "", "local_path": "", "source_url": "",
                            "attachment_id": "", "download_status": "no_attachment", "error": "",
                        })
                        continue
                    attachment_items += 1
                    for source_url in item.attachment_urls:
                        attachment_id = attachment_id_from_url(source_url)
                        status = "failed"
                        error = ""
                        original_filename = local_path = ""
                        try:
                            prior = existing_manifest.get(attachment_id) or existing_manifest.get(source_url)
                            if prior:
                                original_filename = prior["original_filename"]
                                local_path = prior["local_path"]
                                status = "already_exists"
                                existing += 1
                            else:
                                detail_page = await context.new_page()
                                try:
                                    original_filename = ""
                                    if "/common/download.do" in source_url.lower():
                                        head = await detail_page.request.head(source_url, fail_on_status_code=False, timeout=5000)
                                        head_filename = (
                                            filename_from_content_disposition(head.headers.get("content-disposition"))
                                            if head.ok else None
                                        )
                                        original_filename = safe_filename(head_filename) if head_filename else ""
                                        if original_filename and (OUTPUT_DIR / original_filename).exists():
                                            local_path = str(OUTPUT_DIR / original_filename).replace("\\", "/")
                                            status = "already_exists"
                                            existing += 1
                                    if status != "already_exists":
                                        original_filename, body, _ = await discover_file(detail_page, source_url, delay)
                                finally:
                                    await detail_page.close()
                                if status != "already_exists":
                                    original_filename = safe_filename(original_filename)
                                    destination = OUTPUT_DIR / original_filename
                                    if destination.exists():
                                        status = "already_exists"
                                        existing += 1
                                    else:
                                        destination.write_bytes(body)
                                        validation_error = validate_file(destination)
                                        if validation_error:
                                            destination.unlink(missing_ok=True)
                                            raise RuntimeError(validation_error)
                                        status = "downloaded"
                                        downloaded += 1
                                    local_path = str(destination).replace("\\", "/")
                        except Exception as exc:  # keep collecting other public items
                            failures += 1
                            error = f"{type(exc).__name__}: {exc}"
                        rows.append({
                            "item_no": item.item_no, "category": item.category, "title": item.title,
                            "meeting_name": item.meeting_name, "meeting_date": item.meeting_date,
                            "original_filename": original_filename, "local_path": local_path,
                            "source_url": source_url, "attachment_id": attachment_id,
                            "download_status": status, "error": error,
                        })
                        await polite_pause(delay)
        finally:
            await browser.close()
    write_manifest(rows)
    print(f"전체 게시물 수: {total_items}")
    print(f"첨부파일 있는 게시물 수: {attachment_items}")
    print(f"다운로드 성공 수: {downloaded + existing} (신규 {downloaded}, 기존 파일 {existing})")
    print(f"첨부파일 없는 게시물 수: {total_items - attachment_items}")
    print(f"실패 수: {failures}")
    print(f"매니페스트: {MANIFEST_PATH.as_posix()}")
    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=1.5, help="delay in seconds between site requests (default: 1.5)")
    parser.add_argument("--headed", action="store_true", help="show Chromium while collecting")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        raise SystemExit(asyncio.run(run(args.delay, args.headed)))
    except KeyboardInterrupt:
        print("중단되었습니다.", file=sys.stderr)
        raise SystemExit(130)
