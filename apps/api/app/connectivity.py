from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.config import get_settings, missing


TIMEOUT = httpx.Timeout(10.0, connect=5.0)
RETRYABLE = {429, 500, 502, 503, 504}


def result(service: str, ok: bool, **details: Any) -> dict[str, Any]:
    return {"status": "ok" if ok else "error", "service": service, **details}


async def request_json(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in RETRYABLE or attempt == 2:
                return response
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            if attempt == 2:
                raise
        await asyncio.sleep(0.4 * (attempt + 1))
    if last_error:
        raise last_error
    raise RuntimeError("request failed")


async def check_supabase() -> dict[str, Any]:
    settings = get_settings()
    required = ["supabase_url", "supabase_service_role_key"]
    missing_names = missing(required)
    if missing_names:
        return result("supabase", False, error=f"configuration missing: {', '.join(missing_names)}")
    headers = {"apikey": settings.supabase_service_role_key, "Authorization": f"Bearer {settings.supabase_service_role_key}"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await request_json(client, "GET", settings.supabase_url.rstrip("/") + "/rest/v1/", headers=headers)
        return result("supabase", response.is_success, http_status=response.status_code, error=None if response.is_success else "HTTP request failed")
    except Exception:
        return result("supabase", False, error="connection failed")


async def check_openrouter() -> dict[str, Any]:
    settings = get_settings()
    required = ["openrouter_api_key", "openrouter_chat_model", "openrouter_embedding_model"]
    missing_names = missing(required)
    if missing_names:
        return result("openrouter", False, chat_status="not_checked", embedding_status="not_checked", error=f"configuration missing: {', '.join(missing_names)}")
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json", "HTTP-Referer": settings.web_base_url, "X-Title": "AI Inter-Korean Dialogue"}
    base = "https://openrouter.ai/api/v1"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            chat = await request_json(client, "POST", base + "/chat/completions", headers=headers, json={"model": settings.openrouter_chat_model, "messages": [{"role": "user", "content": "Reply exactly with OK."}], "max_tokens": 5, "temperature": 0})
            embedding = await request_json(client, "POST", base + "/embeddings", headers=headers, json={"model": settings.openrouter_embedding_model, "input": "남북회담"})
        chat_payload = chat.json() if chat.headers.get("content-type", "").startswith("application/json") else {}
        embedding_payload = embedding.json() if embedding.headers.get("content-type", "").startswith("application/json") else {}
        chat_ok = chat.is_success and bool(chat_payload.get("choices"))
        embedding_data = embedding_payload.get("data", []) if embedding.is_success else []
        embedding_ok = bool(embedding_data and embedding_data[0].get("embedding"))
        return result(
            "openrouter",
            chat_ok and embedding_ok,
            chat_status="ok" if chat_ok else "error",
            embedding_status="ok" if embedding_ok else "error",
            chat_http_status=chat.status_code,
            embedding_http_status=embedding.status_code,
            chat_error=str(chat_payload.get("error", {}).get("message", ""))[:120] if isinstance(chat_payload.get("error"), dict) else "",
            embedding_error=str(embedding_payload.get("error", {}).get("message", ""))[:120] if isinstance(embedding_payload.get("error"), dict) else "",
            embedding_dimension=len(embedding_data[0]["embedding"]) if embedding_ok else None,
            error=None if chat_ok and embedding_ok else "API response validation failed",
        )
    except Exception:
        return result("openrouter", False, chat_status="error", embedding_status="error", error="connection failed")


async def check_public_data() -> dict[str, Any]:
    settings = get_settings()
    required = ["data_go_kr_api_key", "data_go_kr_api_url"]
    missing_names = missing(required)
    if missing_names:
        return result("public-data", False, error=f"configuration missing: {', '.join(missing_names)}")
    params = {
        "ServiceKey": settings.data_go_kr_api_key,
        "keyword": "남북",
        "thema": "2",
        "bgng_ymd": "20070101",
        "end_ymd": "20071231",
        "country": "북측",
        "numOfRows": 10,
        "pageNo": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await request_json(client, "GET", settings.data_go_kr_api_url, params=params, headers={"Accept": "application/json"})
        payload = response.json()
        header = payload.get("response", {}).get("header", {}) if isinstance(payload, dict) else {}
        if not header and isinstance(payload, dict):
            header = payload.get("header", payload)
            service_error = payload.get("OpenAPI_ServiceResponse", {})
            if isinstance(service_error, dict):
                header = {**header, **service_error}
        body = payload.get("response", {}).get("body", payload) if isinstance(payload, dict) else {}
        items = body.get("items", {}) if isinstance(body, dict) else {}
        raw_items = items.get("item", []) if isinstance(items, dict) else items
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        ok = response.is_success and str(header.get("resultCode", "00")) in {"0", "00", "NORMAL_CODE"} and bool(raw_items)
        return result(
            "public-data",
            ok,
            http_status=response.status_code,
            response_format="json",
            result_code=str(header.get("resultCode", "")),
            result_message=str(header.get("resultMsg", ""))[:120],
            response_keys=sorted(str(key) for key in payload.keys())[:10] if isinstance(payload, dict) else [],
            result_header_path="response.header" if payload.get("response", {}).get("header") else "top-level",
            items_path="response.body.items.item" if payload.get("response", {}).get("body") else "top-level.items",
            item_count=len(raw_items),
            total_count=body.get("totalCount") if isinstance(body, dict) else None,
            page_no=body.get("pageNo") if isinstance(body, dict) else None,
            num_of_rows=body.get("numOfRows") if isinstance(body, dict) else None,
            item_fields=sorted(str(key) for key in raw_items[0].keys()) if raw_items and isinstance(raw_items[0], dict) else [],
            error=None if ok else "API response validation failed",
        )
    except Exception:
        return result("public-data", False, error="connection failed")


async def validate_public_data_parameters() -> dict[str, dict[str, Any]]:
    """After a successful sample call, check each optional search condition once."""
    settings = get_settings()
    params = {
        "ServiceKey": settings.data_go_kr_api_key,
        "keyword": "남북",
        "thema": "2",
        "bgng_ymd": "20070101",
        "end_ymd": "20071231",
        "country": "북측",
        "numOfRows": 10,
        "pageNo": 1,
    }
    results: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for name in ("keyword", "thema", "country", "bgng_ymd", "end_ymd"):
            variant = dict(params)
            variant.pop(name)
            try:
                response = await request_json(client, "GET", settings.data_go_kr_api_url, params=variant, headers={"Accept": "application/json"})
                payload = response.json()
                items = payload.get("items", []) if isinstance(payload, dict) else []
                results[name] = {"http_status": response.status_code, "result_code": payload.get("resultCode", "") if isinstance(payload, dict) else "", "item_count": len(items) if isinstance(items, list) else 0, "total_count": payload.get("totalCount") if isinstance(payload, dict) else None}
            except Exception:
                results[name] = {"http_status": None, "result_code": "error", "item_count": 0, "total_count": None}
    return results
