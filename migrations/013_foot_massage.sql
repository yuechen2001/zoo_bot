-- up
ALTER TABLE users ADD COLUMN massage_active_until TEXT;

-- down
ALTER TABLE users DROP COLUMN massage_active_until;
