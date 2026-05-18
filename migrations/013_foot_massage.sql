-- up
ALTER TABLE users ADD COLUMN massage_active_until TEXT;

-- down
-- SQLite does not support DROP COLUMN on older versions; no-op rollback
SELECT 1;
