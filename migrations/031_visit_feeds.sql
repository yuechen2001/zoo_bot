-- up
CREATE TABLE IF NOT EXISTS visit_feeds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id  INTEGER NOT NULL,
    host_id     INTEGER NOT NULL,
    fed_at      TEXT NOT NULL
);

-- down
DROP TABLE IF EXISTS visit_feeds;
