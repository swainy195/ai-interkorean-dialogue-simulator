from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def main() -> None:
    base = {"ServiceKey": os.environ["DATA_GO_KR_API_KEY"], "bgng_ymd": "19900101", "end_ymd": "20251231", "numOfRows": 10, "pageNo": 1}
    probes = [
        {"name": "date_only", "extra": {}},
        {"name": "keyword", "extra": {"keyword": "남북"}},
        {"name": "theme_1_no_country", "extra": {"keyword": "남북", "thema": "1"}},
        {"name": "theme_1", "extra": {"keyword": "남북", "thema": "1", "country": "북측"}},
        {"name": "theme_2", "extra": {"keyword": "남북", "thema": "2", "country": "북측"}},
        {"name": "theme_3", "extra": {"keyword": "남북", "thema": "3", "country": "북측"}},
        {"name": "theme_4", "extra": {"keyword": "남북", "thema": "4", "country": "북측"}},
        {"name": "theme_5", "extra": {"keyword": "남북", "thema": "5", "country": "북측"}},
        {"name": "theme_6", "extra": {"keyword": "남북", "thema": "6", "country": "북측"}},
    ]
    with httpx.Client(timeout=20, headers={"Accept": "application/json"}) as client:
        for probe in probes:
            params = dict(base)
            params.update(probe["extra"])
            response = client.get(os.environ["DATA_GO_KR_API_URL"], params=params)
            payload = response.json()
            items = payload.get("items", []) if isinstance(payload, dict) else []
            print(probe["name"], response.status_code, payload.get("resultCode"), payload.get("resultMsg"), payload.get("totalCount"), len(items) if isinstance(items, list) else 0)
        print("THEME_1_PAGE_SIZE_10")
        total_items = 0
        for page in range(1, 10):
            params = dict(base, keyword="남북", thema="1", country="북측", numOfRows=10, pageNo=page)
            response = client.get(os.environ["DATA_GO_KR_API_URL"], params=params)
            payload = response.json()
            items = payload.get("items", [])
            total_items += len(items) if isinstance(items, list) else 0
            print("page", page, response.status_code, payload.get("totalCount"), len(items) if isinstance(items, list) else 0)
        print("theme_1_payload_items", total_items)
        print("THEME_1_BOUNDARY_PROBES")
        for rows, page in ((80, 1), (79, 1), (10, 0), (10, 8)):
            params = dict(base, keyword="남북", thema="1", country="북측", numOfRows=rows, pageNo=page)
            response = client.get(os.environ["DATA_GO_KR_API_URL"], params=params)
            payload = response.json()
            items = payload.get("items", [])
            print("rows", rows, "page", page, response.status_code, payload.get("totalCount"), len(items) if isinstance(items, list) else 0)


if __name__ == "__main__":
    main()
