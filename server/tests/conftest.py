from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

_SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://petir:petir@localhost:55433/petir"
)

NODE_ID = "rpi-test-01"
NODE_TOKEN = "test-token-secret"


def _pg_available(url: str) -> bool:
    from sqlalchemy import create_engine, text

    try:
        eng = create_engine(url)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def engine():
    if not _pg_available(TEST_DB_URL):
        pytest.skip(f"no Postgres at {TEST_DB_URL}")
    from sqlalchemy import create_engine

    from app.models import Base

    eng = create_engine(TEST_DB_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def session(engine):
    from sqlalchemy.orm import sessionmaker

    from app.models import Base

    for table in reversed(Base.metadata.sorted_tables):
        with engine.begin() as conn:
            conn.exec_driver_sql(f'TRUNCATE TABLE "{table.name}" CASCADE')
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = maker()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def seeded_node(session):
    from app.ingest.auth import hash_token
    from app.models.registry import EdgeNode

    node = EdgeNode(
        node_id=NODE_ID,
        name="test node",
        api_token_hash=hash_token(NODE_TOKEN),
        enabled=True,
    )
    session.add(node)
    session.commit()
    return node


@pytest.fixture()
def client(engine, seeded_node):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.db import get_session
    from app.ingest.auth import _ingest_limiter
    from app.main import create_app

    _ingest_limiter._buckets.clear()

    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _override():
        s = maker()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_session] = _override
    return TestClient(app, raise_server_exceptions=True)


def auth_headers(token: str = NODE_TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def new_db_epoch() -> str:
    return str(uuid.uuid4())


def new_run_id() -> str:
    return str(uuid.uuid4())
