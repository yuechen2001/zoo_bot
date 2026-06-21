-- up
CREATE TABLE IF NOT EXISTS users (
    user_id            INTEGER PRIMARY KEY,
    username           TEXT,
    group_chat_id      INTEGER,
    coins              INTEGER NOT NULL DEFAULT 100,
    streak_windows     INTEGER NOT NULL DEFAULT 0,
    consecutive_misses INTEGER NOT NULL DEFAULT 0,
    last_prompt_at     TEXT,
    last_checkin_at    TEXT,
    paused_until       TEXT,
    opted_in           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS species (
    species_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    emoji          TEXT NOT NULL,
    rarity         TEXT NOT NULL,
    catch_rate     REAL NOT NULL,
    catch_cost     INTEGER NOT NULL,
    hunger_decay   INTEGER NOT NULL DEFAULT 5,
    breed_time_hrs INTEGER NOT NULL DEFAULT 24,
    habitat        TEXT
);

CREATE TABLE IF NOT EXISTS animals (
    animal_id      TEXT PRIMARY KEY,
    user_id        INTEGER REFERENCES users(user_id),
    species_id     INTEGER REFERENCES species(species_id),
    nickname       TEXT,
    hunger         INTEGER NOT NULL DEFAULT 100,
    happiness      INTEGER NOT NULL DEFAULT 100,
    level          INTEGER NOT NULL DEFAULT 1,
    xp             INTEGER NOT NULL DEFAULT 0,
    is_breeding    INTEGER NOT NULL DEFAULT 0,
    caught_at      TEXT DEFAULT (datetime('now')),
    hunger_alerted INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS breeding_queue (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER REFERENCES users(user_id),
    parent_a             TEXT REFERENCES animals(animal_id),
    parent_b             TEXT REFERENCES animals(animal_id),
    offspring_species_id INTEGER REFERENCES species(species_id),
    ready_at             TEXT NOT NULL,
    collected            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mood_checkins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER REFERENCES users(user_id),
    emoji         TEXT,
    coins_earned  INTEGER,
    streak_window INTEGER,
    checked_in_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id         INTEGER REFERENCES users(user_id),
    achievement_key TEXT NOT NULL,
    earned_at       TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, achievement_key)
);

CREATE TABLE IF NOT EXISTS trivia_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER REFERENCES users(user_id),
    asked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(user_id),
    claimed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    proposer_id         INTEGER NOT NULL REFERENCES users(user_id),
    recipient_id        INTEGER NOT NULL REFERENCES users(user_id),
    proposer_animal_id  TEXT NOT NULL REFERENCES animals(animal_id),
    recipient_animal_id TEXT NOT NULL REFERENCES animals(animal_id),
    created_at          TEXT DEFAULT (datetime('now')),
    status              TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS prompt_responses (
    group_chat_id  INTEGER NOT NULL,
    prompt_sent_at TEXT NOT NULL,
    user_id        INTEGER NOT NULL REFERENCES users(user_id),
    PRIMARY KEY (group_chat_id, prompt_sent_at, user_id)
);

CREATE TABLE IF NOT EXISTS investments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER REFERENCES users(user_id),
    amount        INTEGER NOT NULL,
    return_amount INTEGER NOT NULL,
    invested_at   TEXT DEFAULT (datetime('now')),
    collected     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_enclosures (
    user_id INTEGER REFERENCES users(user_id),
    habitat TEXT NOT NULL,
    level   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, habitat)
);

-- down
DROP TABLE IF EXISTS user_enclosures;
DROP TABLE IF EXISTS investments;
DROP TABLE IF EXISTS prompt_responses;
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS daily_log;
DROP TABLE IF EXISTS trivia_log;
DROP TABLE IF EXISTS user_achievements;
DROP TABLE IF EXISTS mood_checkins;
DROP TABLE IF EXISTS breeding_queue;
DROP TABLE IF EXISTS animals;
DROP TABLE IF EXISTS species;
DROP TABLE IF EXISTS users;
