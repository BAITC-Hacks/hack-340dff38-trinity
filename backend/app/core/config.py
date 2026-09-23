from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str = "sqlite:///./sana.db"
    ai_mode: Literal["mock", "claude"] = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    )
    demo_auth_enabled: bool = True
    demo_tools_enabled: bool = True
    demo_access_code: str = ""


@lru_cache
def settings():
    return Settings()
