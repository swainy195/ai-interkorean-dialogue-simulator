"""Run explicit, one-shot connectivity checks without printing secrets."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.connectivity import check_openrouter, check_public_data, check_supabase, validate_public_data_parameters


async def main() -> int:
    checks = {
        "Supabase": await check_supabase(),
        "OpenRouter Chat + Embeddings": await check_openrouter(),
        "Public Data API": await check_public_data(),
    }
    print("Connection Check")
    for label, item in checks.items():
        print(f"{label}: {item['status'].upper()}")
        for field in ("chat_status", "embedding_status", "chat_http_status", "embedding_http_status", "chat_error", "embedding_error", "http_status", "result_code", "result_message", "response_keys"):
            if field in item:
                print(f"  {field}: {item[field]}")
        if item.get("error"):
            print(f"  reason: {item['error']}")
        if item.get("embedding_dimension"):
            print(f"  embedding_dimension: {item['embedding_dimension']}")
        for field in ("item_count", "total_count", "page_no", "num_of_rows", "item_fields"):
            if field in item:
                print(f"  {field}: {item[field]}")
    if checks["Public Data API"]["status"] == "ok":
        print("Public Data Parameter Removal Checks")
        for name, item in (await validate_public_data_parameters()).items():
            print(f"  remove_{name}: HTTP {item['http_status']}, resultCode={item['result_code']}, item_count={item['item_count']}, totalCount={item['total_count']}")
    passed = all(item["status"] == "ok" for item in checks.values())
    print(f"Overall: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
