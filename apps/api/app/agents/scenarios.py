from __future__ import annotations

SCENARIOS = {
    "separated_families": {"title": "이산가족 상봉 재개", "south_goal": "상봉 재개·정례화·생사확인·단계적 확대", "north_goal": "상호 관심사항 고려·단계적 협의·자측 조건 반영"},
    "transport_cooperation": {"title": "남북 철도·도로 및 물류 협력", "south_goal": "공동조사·실무협의체·단계적 연결과 협력", "north_goal": "조건부 협력·상호주의·단계별 추진"},
    "military_tension": {"title": "군사적 긴장완화", "south_goal": "우발충돌 방지·연락체계·실무협의·단계적 신뢰구축", "north_goal": "상호 조치·일방적 요구 거부·자측 우려 반영"},
}


def get_scenario(key: str) -> dict[str, str]:
    if key not in SCENARIOS:
        raise ValueError(f"unknown scenario: {key}")
    return SCENARIOS[key]
