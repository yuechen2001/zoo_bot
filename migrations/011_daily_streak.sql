-- up
ALTER TABLE users ADD COLUMN daily_streak INTEGER NOT NULL DEFAULT 0;

-- down
ALTER TABLE users DROP COLUMN daily_streak;
