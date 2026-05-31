from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    server_url: str
    node_id: str
    node_token: str
    edge_db_path: str
    request_timeout_s: float
    max_retries: int
    backoff_base_s: float
    backoff_cap_s: float

    @property
    def sync_batch_url(self) -> str:
        return self.server_url.rstrip("/") + "/api/ingest/sync-batch"


def _require(name: str, env: dict[str, str]) -> str:
    value = env.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def load_config(env: dict[str, str] | None = None) -> Config:
    env = dict(os.environ if env is None else env)
    return Config(
        server_url=_require("SERVER_URL", env),
        node_id=_require("NODE_ID", env),
        node_token=_require("NODE_TOKEN", env),
        edge_db_path=_require("EDGE_DB_PATH", env),
        request_timeout_s=float(env.get("REQUEST_TIMEOUT_S", "10")),
        max_retries=int(env.get("MAX_RETRIES", "3")),
        backoff_base_s=float(env.get("BACKOFF_BASE_S", "2")),
        backoff_cap_s=float(env.get("BACKOFF_CAP_S", "30")),
    )
