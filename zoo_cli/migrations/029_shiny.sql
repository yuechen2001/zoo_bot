-- up
ALTER TABLE animals ADD COLUMN is_shiny INTEGER NOT NULL DEFAULT 0;

-- down
ALTER TABLE animals DROP COLUMN is_shiny;
