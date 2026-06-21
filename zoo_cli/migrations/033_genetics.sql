-- up
ALTER TABLE animals ADD COLUMN stat_speed       INTEGER NOT NULL DEFAULT 50;
ALTER TABLE animals ADD COLUMN stat_rarity      INTEGER NOT NULL DEFAULT 50;
ALTER TABLE animals ADD COLUMN stat_temperament INTEGER NOT NULL DEFAULT 50;

-- down
-- SQLite does not support DROP COLUMN on older versions; rollback manually if needed
