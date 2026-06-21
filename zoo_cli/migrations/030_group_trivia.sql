-- up
CREATE TABLE IF NOT EXISTS group_trivia (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    group_chat_id INTEGER NOT NULL,
    correct_answer TEXT NOT NULL,
    fired_at     TEXT NOT NULL,
    expires_at   TEXT NOT NULL,
    message_id   INTEGER,
    resolved     INTEGER NOT NULL DEFAULT 0,
    answered_by  INTEGER
);

-- down
DROP TABLE IF EXISTS group_trivia;
