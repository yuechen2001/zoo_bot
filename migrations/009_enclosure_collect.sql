-- up
ALTER TABLE users ADD COLUMN pending_enclosure_coins INTEGER NOT NULL DEFAULT 0;

-- down
ALTER TABLE users DROP COLUMN pending_enclosure_coins;
