-- up
CREATE TABLE IF NOT EXISTS group_state (
    group_chat_id  INTEGER PRIMARY KEY,
    last_prompt_at TEXT DEFAULT NULL
);

-- down
DROP TABLE IF EXISTS group_state;
