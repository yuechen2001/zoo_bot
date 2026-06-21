-- up
CREATE TABLE IF NOT EXISTS wild_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    group_chat_id     INTEGER NOT NULL,
    species_id        INTEGER NOT NULL,
    message_id        INTEGER,
    created_at        TEXT DEFAULT (datetime('now')),
    caught_by_user_id INTEGER
);

-- down
DROP TABLE IF EXISTS wild_events;
