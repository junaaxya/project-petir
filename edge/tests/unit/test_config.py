from __future__ import annotations

import pytest

from sync_worker.config import load_config


_REQUIRED = {
    "SERVER_URL": "https://petir.invalid",
    "NODE_ID": "rpi-test",
    "NODE_TOKEN": "secret",
    "EDGE_DB_PATH": ":memory:",
}


def test_strict_first_sync_defaults_off():
    assert load_config(_REQUIRED).strict_first_sync is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_strict_first_sync_accepts_true_values(value):
    assert load_config({**_REQUIRED, "STRICT_FIRST_SYNC": value}).strict_first_sync


def test_strict_first_sync_rejects_invalid_boolean():
    with pytest.raises(RuntimeError, match="STRICT_FIRST_SYNC"):
        load_config({**_REQUIRED, "STRICT_FIRST_SYNC": "sometimes"})