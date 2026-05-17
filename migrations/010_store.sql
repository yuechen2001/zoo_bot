-- up
ALTER TABLE users ADD COLUMN lucky_catch_active INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN active_title TEXT;
CREATE TABLE IF NOT EXISTS user_purchases (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    item_key     TEXT NOT NULL,
    purchased_at TEXT DEFAULT (datetime('now'))
);

-- down
DROP TABLE IF EXISTS user_purchases;
SELECT 1;
