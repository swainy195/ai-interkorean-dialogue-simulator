"""Measure local Phase 9 HTTP baselines without printing secrets."""

from __future__ import annotations

import json
import time
from urllib.request import Request, urlopen


BASE = "http://127.0.0.1:8000"


def request(method: str, path: str, payload: dict | None = None) -> tuple[int, float, dict]:
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(BASE + path, data=body, method=method, headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urlopen(req, timeout=180) as response:
        elapsed = (time.perf_counter() - started) * 1000
        return response.status, elapsed, json.loads(response.read())


def main() -> None:
    health_status, health_ms, _ = request("GET", "/health")
    create_status, create_ms, created = request("POST", "/api/v1/simulations", {"scenario": "separated_families", "mode": "AI_VS_AI", "relationship_state": "neutral", "max_rounds": 6})
    turn_status, turn_ms, turn = request("POST", f"/api/v1/simulations/{created['session_id']}/next")
    print(json.dumps({"health": {"status": health_status, "ms": round(health_ms, 1)}, "create": {"status": create_status, "ms": round(create_ms, 1)}, "warm_turn": {"status": turn_status, "ms": round(turn_ms, 1), "evidence_count": len(turn.get("turn", {}).get("evidence", [])), "result": bool(turn.get("result"))}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
