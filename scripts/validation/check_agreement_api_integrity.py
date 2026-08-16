from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def document_id(item: dict[str, Any]) -> str:
    raw = "|".join(str(item.get(key) or "").strip() for key in ("title", "agmnt_ymd", "url", "filenm"))
    return "agreement:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_key(item: dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def query(client: httpx.Client, theme: str | None) -> dict[str, Any]:
    params = {"ServiceKey": os.environ["DATA_GO_KR_API_KEY"], "bgng_ymd": "19900101", "end_ymd": "20251231", "numOfRows": 100, "pageNo": 1}
    if theme is not None:
        params["thema"] = theme
    all_items: list[dict[str, Any]] = []
    total_count = 0
    pages = []
    while True:
        response = client.get(os.environ["DATA_GO_KR_API_URL"], params=params)
        payload = response.json()
        items = payload.get("items", []) if isinstance(payload, dict) else []
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        pages.append({"page": params["pageNo"], "http_status": response.status_code, "total_count": payload.get("totalCount"), "payload_count": len(items), "result_code": payload.get("resultCode")})
        all_items.extend(items)
        total_count = int(payload.get("totalCount") or 0)
        if not items or len(all_items) >= total_count:
            break
        params["pageNo"] += 1
    document_ids = {document_id(item) for item in all_items}
    title_dates = {(str(item.get("title") or "").strip(), str(item.get("agmnt_ymd") or "").strip()) for item in all_items}
    exact = [record_key(item) for item in all_items]
    return {"theme": theme or "none", "total_count": total_count, "payload": len(all_items), "document_unique": len(document_ids), "title_date_unique": len(title_dates), "exact_duplicate_count": len(exact) - len(set(exact)), "theme_values": sorted({str(item.get("thema")) for item in all_items}), "pages": pages}


def main() -> None:
    with httpx.Client(timeout=20, headers={"Accept": "application/json"}) as client:
        results = [query(client, theme) for theme in (None, "1", "2")]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
