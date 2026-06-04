-- up
ALTER TABLE species ADD COLUMN is_special INTEGER NOT NULL DEFAULT 0;

-- down
ALTER TABLE species DROP COLUMN is_special;
