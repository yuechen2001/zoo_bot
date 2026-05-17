-- up
ALTER TABLE users ADD COLUMN pending_enclosure_coins INTEGER NOT NULL DEFAULT 0;

-- down
-- SQLite does not support DROP COLUMN on older versions; no-op rollback
SELECT 1;
