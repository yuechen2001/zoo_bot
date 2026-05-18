-- up
-- Repairs deployments where 014 was recorded as applied but never executed
-- (missing "-- up" header caused executescript("") to run silently).
-- migrate.py silently ignores "duplicate column name" errors so these are idempotent.
ALTER TABLE users ADD COLUMN mood_booster_active INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN catch_net_active    INTEGER NOT NULL DEFAULT 0;

-- down
SELECT 1;
