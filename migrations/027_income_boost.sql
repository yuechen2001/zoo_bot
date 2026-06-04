-- up
ALTER TABLE users ADD COLUMN income_boost_expires_at TEXT;

-- down
ALTER TABLE users DROP COLUMN income_boost_expires_at;
