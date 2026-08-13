from __future__ import annotations

from tests.conftest import NODE_ID


def test_forecast_latest_returns_empty_items_when_no_forecasts_exist(client, seeded_node):
    r = client.get("/api/forecast/latest")
    assert r.status_code == 200

    body = r.json()
    assert body["node_id"] == NODE_ID
    assert body["computed_at_utc"] is None
    assert body["items"] == []