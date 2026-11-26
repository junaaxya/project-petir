from __future__ import annotations

import ipaddress
from typing import Literal

from petir_contracts import CONTRACT_VERSION
from pydantic import field_validator
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
    cloudflare_jwks_proxy_url: str = ""
    health_response_mode: Literal["public_safe", "legacy_full"] = "public_safe"
    public_data_mode: Literal["public_safe", "legacy_full"] = "public_safe"
    api_docs_enabled: bool = True
    siren_audit_enabled: bool = False
    siren_audit_cooldown_seconds: int = 60
    siren_audit_operators_json: str = ""

    rate_limit_per_node: int = 120
    rate_limit_window_seconds: int = 60
    invalid_bearer_max_failures: int = 10
    invalid_bearer_window_seconds: int = 60
    invalid_bearer_block_seconds: int = 300
    invalid_bearer_max_clients: int = 10_000
    trusted_proxy_cidrs: str = ""
    query_statement_timeout_ms: int = 3_000
    export_statement_timeout_ms: int = 5_000
    query_max_page_rows: int = 10_000
    history_max_buckets: int = 10_000
    weather_raw_estimated_rows_per_minute: int = 12
    weather_raw_max_estimated_rows: int = 150_000
    quality_max_estimated_minute_rows: int = 600_000
    lightning_event_estimated_rows_per_minute: int = 2
    lightning_event_max_estimated_rows: int = 300_000
    lightning_export_max_estimated_rows: int = 100_000
    availability_check_enabled: bool = True
    availability_recovery_status: str = "fresh"
    availability_server_event_epoch: str = "00000000-0000-0000-0000-000000000001"
    wan_failover_snapshot_dir: str = ""

    cors_allow_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @field_validator("trusted_proxy_cidrs")
    @classmethod
    def validate_trusted_proxy_cidrs(cls, value: str) -> str:
        for item in value.split(","):
            item = item.strip()
            if item:
                ipaddress.ip_network(item, strict=False)
        return value


settings = Settings()
