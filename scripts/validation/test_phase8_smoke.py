"""Live Phase 8 API smoke: one AI stream and one User-vs-AI turn."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    with TestClient(app) as client:
        ai = client.post("/api/v1/simulations", json={"scenario": "separated_families", "mode": "AI_VS_AI", "max_rounds": 6})
        ai.raise_for_status()
        stream = client.post(f"/api/v1/simulations/{ai.json()['session_id']}/next/stream")
        stream.raise_for_status()
        user = client.post("/api/v1/simulations", json={"scenario": "separated_families", "mode": "USER_SOUTH_VS_AI_NORTH", "max_rounds": 6})
        user.raise_for_status()
        user_body = client.post(f"/api/v1/simulations/{user.json()['session_id']}/user-turn", json={"message": "생사확인과 단계적 상봉 재개를 위한 실무협의를 제안합니다."})
        user_body.raise_for_status()
    print(json.dumps({"ai_vs_ai": {"stream_http": stream.status_code, "has_thinking": "event: agent_state" in stream.text, "has_tokens": "event: token" in stream.text, "has_done": "event: done" in stream.text}, "user_vs_ai": {"http": user_body.status_code, "user_message_preserved": user_body.json()["user_turn"]["message"], "ai_speaker": user_body.json()["turn"]["speaker_agent_id"], "evidence_count": len(user_body.json()["turn"].get("evidence", []))}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
