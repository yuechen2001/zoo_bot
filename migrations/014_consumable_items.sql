-- up
ALTER TABLE users ADD COLUMN mood_booster_active INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN catch_net_active    INTEGER NOT NULL DEFAULT 0;

-- down
SELECT 1;
