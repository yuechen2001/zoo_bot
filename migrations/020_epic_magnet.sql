-- up
ALTER TABLE users ADD COLUMN epic_magnet_active INTEGER NOT NULL DEFAULT 0;

-- down
ALTER TABLE users DROP COLUMN epic_magnet_active;
