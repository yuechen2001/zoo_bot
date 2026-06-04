-- up
ALTER TABLE user_quest_progress ADD COLUMN tasks_skipped INTEGER NOT NULL DEFAULT 0;

-- down
ALTER TABLE user_quest_progress DROP COLUMN tasks_skipped;
