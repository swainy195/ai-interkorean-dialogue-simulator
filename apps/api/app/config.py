from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[3] / ".env")


@dataclass(frozen=True)
class Settings:
    supabase_url: str = os.getenv("SUPABASE_URL", "").strip()
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "").strip()
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    supabase_db_url: str = os.getenv("SUPABASE_DB_URL", "").strip()
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()
    openrouter_chat_model: str = os.getenv("OPENROUTER_CHAT_MODEL", "").strip()
    openrouter_embedding_model: str = os.getenv("OPENROUTER_EMBEDDING_MODEL", "").strip()
    data_go_kr_api_key: str = os.getenv("DATA_GO_KR_API_KEY", "").strip()
    data_go_kr_api_url: str = os.getenv("DATA_GO_KR_API_URL", "").strip()
    web_base_url: str = os.getenv("WEB_BASE_URL", "http://localhost:5173").strip()


def get_settings() -> Settings:
    return Settings()


def missing(names: list[str]) -> list[str]:
    settings = get_settings()
    env_names = {
        "supabase_url": "SUPABASE_URL",
        "supabase_service_role_key": "SUPABASE_SERVICE_ROLE_KEY",
        "openrouter_api_key": "OPENROUTER_API_KEY",
        "openrouter_chat_model": "OPENROUTER_CHAT_MODEL",
        "openrouter_embedding_model": "OPENROUTER_EMBEDDING_MODEL",
        "data_go_kr_api_key": "DATA_GO_KR_API_KEY",
        "data_go_kr_api_url": "DATA_GO_KR_API_URL",
    }
    return [env_names.get(name, name) for name in names if not getattr(settings, name)]
