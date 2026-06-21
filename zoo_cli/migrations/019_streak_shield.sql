-- up
ALTER TABLE users ADD COLUMN streak_shield_active INTEGER NOT NULL DEFAULT 0;

-- down
ALTER TABLE users DROP COLUMN streak_shield_active;
