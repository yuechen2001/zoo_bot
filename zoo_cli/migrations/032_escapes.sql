-- up
CREATE TABLE IF NOT EXISTS animal_escapes (
    escape_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id     TEXT NOT NULL,
    user_id       INTEGER NOT NULL,
    group_chat_id INTEGER NOT NULL,
    escaped_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    message_id    INTEGER,
    resolved      INTEGER NOT NULL DEFAULT 0
);
-- down
DROP TABLE IF EXISTS animal_escapes;
