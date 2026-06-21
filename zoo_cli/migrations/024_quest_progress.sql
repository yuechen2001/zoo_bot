-- up
CREATE TABLE IF NOT EXISTS user_quest_progress (
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    chapter_num INTEGER NOT NULL,
    step        INTEGER NOT NULL DEFAULT 0,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    PRIMARY KEY (user_id, chapter_num)
);

ALTER TABLE users ADD COLUMN feeds_given INTEGER NOT NULL DEFAULT 0;

-- down
DROP TABLE IF EXISTS user_quest_progress;
