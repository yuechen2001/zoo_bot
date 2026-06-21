-- up
ALTER TABLE breeding_queue ADD COLUMN last_notified_at TEXT;

-- down
ALTER TABLE breeding_queue DROP COLUMN last_notified_at;
