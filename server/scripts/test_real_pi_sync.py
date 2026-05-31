from __future__ import annotations

import os
import sqlite3
import sys
import uuid
from collections import defaultdict

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "edge"))

from sync_worker import cursors, readers, run_record
from sync_worker.client import SyncClient
from sync_worker.config import Config
from sync_worker.run import _build_envelope, _now_iso, _accepted_value
from sync_worker.tables import PRIORITY_ORDER
from petir_contracts import CursorStrategy

config = Config(
    server_url=os.environ.get("SYNC_REPLAY_SERVER_URL", "http://127.0.0.1:8000"),
    node_id=os.environ.get("SYNC_REPLAY_NODE_ID", "rpi-lab-01"),
    node_token=os.environ.get("SYNC_REPLAY_NODE_TOKEN", "dev-token"),
    edge_db_path=os.environ.get("SYNC_REPLAY_EDGE_DB_PATH", "/tmp/weather_copy.db"),
    request_timeout_s=30.0,
    max_retries=2,
    backoff_base_s=1.0,
    backoff_cap_s=5.0,
)

conn = sqlite3.connect(config.edge_db_path)
cursors.ensure_local_tables(conn)
run_record.ensure_run_table(conn)
db_epoch = cursors.get_or_create_db_epoch(conn)
run_id = str(uuid.uuid4())

client = SyncClient(config)

stats: dict[str, dict] = defaultdict(lambda: {"accepted": 0, "rejected": 0, "batches": 0, "reasons": defaultdict(int), "samples": []})
seq = 0

try:
    for cfg in PRIORITY_ORDER:
        while True:
            cursor_value = cursors.read_cursor(conn, cfg.name, cfg.strategy)
            rows = readers.read_rows(conn, cfg, cursor_value)
            if not rows:
                break
            seq += 1
            env = _build_envelope(config, db_epoch, run_id, cfg, cursor_value, rows, seq)
            resp = client.post_batch(env)
            s = stats[cfg.name]
            s["accepted"] += resp.accepted
            s["rejected"] += len(resp.rejected)
            s["batches"] += 1
            for rr in resp.rejected:
                key = f"{rr.field}: {rr.reason}"
                s["reasons"][key] += 1
                if len(s["samples"]) < 3:
                    s["samples"].append({"index": rr.index, "field": rr.field, "reason": rr.reason})
            adv = _accepted_value(resp.accepted_cursor, cfg.strategy)
            if adv is not None:
                cursors.advance_cursor(conn, cfg.name, cfg.strategy, adv, resp.accepted, _now_iso())
            if len(rows) < cfg.limit:
                break
finally:
    client.close()
    conn.close()

print("=" * 70)
print(f"{'TABLE':<28} {'ACCEPTED':>10} {'REJECTED':>10} {'BATCHES':>8}")
print("-" * 70)
ta = tr = 0
for cfg in PRIORITY_ORDER:
    s = stats[cfg.name]
    ta += s["accepted"]; tr += s["rejected"]
    print(f"{cfg.name:<28} {s['accepted']:>10} {s['rejected']:>10} {s['batches']:>8}")
print("-" * 70)
print(f"{'TOTAL':<28} {ta:>10} {tr:>10}")
print("=" * 70)
for cfg in PRIORITY_ORDER:
    s = stats[cfg.name]
    if s["rejected"]:
        print(f"\n[{cfg.name}] rejection reasons:")
        for k, v in s["reasons"].items():
            print(f"   {v}x  {k}")
        for ex in s["samples"]:
            print(f"   sample: {ex}")
