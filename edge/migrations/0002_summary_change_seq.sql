CREATE TABLE IF NOT EXISTS change_seq_counter (
    table_name TEXT PRIMARY KEY,
    value      INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO change_seq_counter(table_name, value) VALUES ('weather_minute_summary', 0);
INSERT OR IGNORE INTO change_seq_counter(table_name, value) VALUES ('lightning_minute_summary', 0);

CREATE TRIGGER IF NOT EXISTS wms_change_seq_ins
AFTER INSERT ON weather_minute_summary
BEGIN
    UPDATE change_seq_counter SET value = value + 1 WHERE table_name = 'weather_minute_summary';
    UPDATE weather_minute_summary
       SET change_seq = (SELECT value FROM change_seq_counter WHERE table_name = 'weather_minute_summary')
     WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS wms_change_seq_upd
AFTER UPDATE ON weather_minute_summary
WHEN NEW.change_seq IS OLD.change_seq
BEGIN
    UPDATE change_seq_counter SET value = value + 1 WHERE table_name = 'weather_minute_summary';
    UPDATE weather_minute_summary
       SET change_seq = (SELECT value FROM change_seq_counter WHERE table_name = 'weather_minute_summary')
     WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS lms_change_seq_ins
AFTER INSERT ON lightning_minute_summary
BEGIN
    UPDATE change_seq_counter SET value = value + 1 WHERE table_name = 'lightning_minute_summary';
    UPDATE lightning_minute_summary
       SET change_seq = (SELECT value FROM change_seq_counter WHERE table_name = 'lightning_minute_summary')
     WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS lms_change_seq_upd
AFTER UPDATE ON lightning_minute_summary
WHEN NEW.change_seq IS OLD.change_seq
BEGIN
    UPDATE change_seq_counter SET value = value + 1 WHERE table_name = 'lightning_minute_summary';
    UPDATE lightning_minute_summary
       SET change_seq = (SELECT value FROM change_seq_counter WHERE table_name = 'lightning_minute_summary')
     WHERE rowid = NEW.rowid;
END;
