from __future__ import annotations

from typing import Literal

from petir_contracts import CONTRACT_VERSION
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://petir:petir@localhost:5432/petir"
    contract_version: str = CONTRACT_VERSION

    dashboard_api_key: str = ""
    dashboard_auth_enabled: bool = False
    admin_auth_mode: Literal[
        "disabled", "api_key", "cloudflare_access", "legacy_dashboard"
    ] = "disabled"
    admin_api_key: str = ""
    operator_api_key: str = ""
    cloudflare_access_team_domain: str = ""
    cloudflare_access_audience: str = ""
    cloudflare_access_admin_emails: str = ""
    cloudflare_access_operator_emails: str = ""
    api_docs_enabled: bool = True
    siren_audit_enabled: bool = False
    siren_audit_cooldown_seconds: int = 60
    siren_audit_operators_json: str = ""

    rate_limit_per_node: int = 120
    rate_limit_window_seconds: int = 60
    availability_check_enabled: bool = True
    availability_recovery_status: str = "fresh"
    availability_server_event_epoch: str = "00000000-0000-0000-0000-000000000001"
    wan_failover_snapshot_dir: str = ""

    cors_allow_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


settings = Settings()
