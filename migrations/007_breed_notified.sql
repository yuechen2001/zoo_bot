-- up
ALTER TABLE breeding_queue ADD COLUMN last_notified_at TEXT;

-- down
-- SQLite does not support DROP COLUMN on older versions; no-op rollback
SELECT 1;
