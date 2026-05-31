from __future__ import annotations

import os
import sqlite3
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SERVER = _ROOT / "server"
_EDGE = _ROOT / "edge"
for p in (str(_SERVER), str(_EDGE)):
    if p not in sys.path:
        sys.path.insert(0, p)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://petir:petir@localhost:55434/petir"
)
NODE_ID = "rpi-e2e-01"
NODE_TOKEN = "e2e-token"


def _pg_ready(url: str) -> bool:
    from sqlalchemy import create_engine, text

    try:
        eng = create_engine(url)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:
        return False


class ServerHandle:
    def __init__(self, port: int) -> None:
        self.port = port
        self._server = None
        self._thread = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        import uvicorn

        from app.main import create_app

        config = uvicorn.Config(
            create_app(), host="127.0.0.1", port=self.port, log_level="warning"
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        for _ in range(100):
            if getattr(self._server, "started", False):
                return
            time.sleep(0.05)
        raise RuntimeError("uvicorn did not start")

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=10)
        self._server = None
        self._thread = None


@pytest.fixture(scope="session")
def _require_pg():
    if not _pg_ready(DATABASE_URL):
        pytest.skip(f"no Postgres at {DATABASE_URL}")


@pytest.fixture()
def pg_engine(_require_pg):
    from sqlalchemy import create_engine

    os.environ["DATABASE_URL"] = DATABASE_URL
    from app.models import Base

    eng = create_engine(DATABASE_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def seeded_node(pg_engine):
    from sqlalchemy.orm import sessionmaker

    from app.ingest.auth import hash_token
    from app.models.registry import EdgeNode

    maker = sessionmaker(bind=pg_engine, expire_on_commit=False)
    s = maker()
    s.add(EdgeNode(node_id=NODE_ID, name="e2e", api_token_hash=hash_token(NODE_TOKEN), enabled=True))
    s.commit()
    s.close()


@pytest.fixture()
def server(pg_engine, seeded_node):
    handle = ServerHandle(port=8077)
    handle.start()
    yield handle
    handle.stop()


def _free_port() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture()
def edge_db(tmp_path):
    path = str(tmp_path / "weather_edge.db")
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts_pi_utc TEXT NOT NULL,
            source TEXT, level TEXT, event_type TEXT, message TEXT,
            details_json TEXT, created_at_utc TEXT NOT NULL
        );
        CREATE TABLE weather_minute_summary (
            minute_utc TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL,
            sample_count INTEGER, status TEXT, temperature_avg REAL,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY (minute_utc, source, device)
        );
        CREATE TABLE lightning_minute_summary (
            minute_utc TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL,
            status TEXT, updated_at_utc TEXT NOT NULL,
            PRIMARY KEY (minute_utc, source, device)
        );
        CREATE TABLE lightning_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts_pi_utc TEXT NOT NULL,
            event_type TEXT, created_at_utc TEXT NOT NULL
        );
        CREATE TABLE weather_quality_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at_utc TEXT NOT NULL
        );
        CREATE TABLE weather_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts_pi_utc TEXT NOT NULL,
            created_at_utc TEXT NOT NULL
        );
        """
    )
    for i in range(1, 6):
        conn.execute(
            "INSERT INTO system_events(ts_pi_utc, level, event_type, message, created_at_utc) "
            "VALUES(?,?,?,?,?)",
            (f"2026-05-30T03:1{i}:00Z", "info", "boot", f"e{i}", f"2026-05-30T03:1{i}:00Z"),
        )
    for i in range(1, 4):
        conn.execute(
            "INSERT INTO weather_minute_summary(minute_utc, source, device, sample_count, "
            "status, temperature_avg, updated_at_utc) VALUES(?,?,?,?,?,?,?)",
            (f"2026-05-30T03:0{i}:00Z", "arduino", "weather-01", 12, "ok", 27.0 + i,
             f"2026-05-30T03:0{i}:30Z"),
        )
    conn.commit()
    conn.close()

    from migrations.apply import apply_migration

    apply_migration(path, do_backup=False)
    return path


def make_config(base_url: str, db_path: str):
    from sync_worker.config import Config

    return Config(
        server_url=base_url,
        node_id=NODE_ID,
        node_token=NODE_TOKEN,
        edge_db_path=db_path,
        request_timeout_s=2.0,
        max_retries=1,
        backoff_base_s=0.0,
        backoff_cap_s=0.0,
    )
