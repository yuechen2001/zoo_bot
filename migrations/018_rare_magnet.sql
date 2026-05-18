-- up
ALTER TABLE users ADD COLUMN rare_magnet_active INTEGER NOT NULL DEFAULT 0;

-- down
ALTER TABLE users DROP COLUMN rare_magnet_active;
