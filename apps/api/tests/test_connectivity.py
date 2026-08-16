import httpx
import asyncio

from app.connectivity import request_json


def test_request_json_retries_retryable_response() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503 if calls < 3 else 200, json={"ok": True})

    async def run() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await request_json(client, "GET", "https://example.test")

    response = asyncio.run(run())

    assert response.status_code == 200
    assert calls == 3
