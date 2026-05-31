from __future__ import annotations

from petir_contracts import CONTRACT_VERSION
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://petir:petir@localhost:5432/petir"
    contract_version: str = CONTRACT_VERSION

    dashboard_api_key: str = ""
    dashboard_auth_enabled: bool = False

    rate_limit_per_node: int = 120
    rate_limit_window_seconds: int = 60

    cors_allow_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


settings = Settings()
