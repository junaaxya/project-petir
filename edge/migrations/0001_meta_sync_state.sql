CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
    table_name      TEXT PRIMARY KEY,
    last_edge_id    INTEGER,
    last_change_seq INTEGER,
    last_acked_at   TEXT,
    rows_sent       INTEGER NOT NULL DEFAULT 0
);
