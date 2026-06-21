"""
Tests for db.py functions with non-trivial logic.
Simple CRUD wrappers are not tested here — they're thin SQL and would
just duplicate the schema. Only functions with branching, aggregation,
atomicity, or multi-step state changes are covered.
"""

import sqlite3
import pytest
import db


_SCHEMA = """
CREATE TABLE species (
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
CREATE TABLE users (
    user_id                 INTEGER PRIMARY KEY,
    username                TEXT,
    group_chat_id           INTEGER,
    coins                   INTEGER NOT NULL DEFAULT 100,
    streak_windows          INTEGER NOT NULL DEFAULT 0,
    consecutive_misses      INTEGER NOT NULL DEFAULT 0,
    last_prompt_at          TEXT,
    last_checkin_at         TEXT,
    paused_until            TEXT,
    opted_in                INTEGER NOT NULL DEFAULT 1,
    autofeed_threshold      INTEGER,
    autofeed_max_coins      INTEGER,
    pending_enclosure_coins INTEGER NOT NULL DEFAULT 0,
    lucky_catch_active      INTEGER NOT NULL DEFAULT 0,
    active_title            TEXT,
    massage_active_until    TEXT,
    daily_streak            INTEGER NOT NULL DEFAULT 0,
    mood_booster_active     INTEGER NOT NULL DEFAULT 0,
    catch_net_active        INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE animals (
    animal_id      TEXT PRIMARY KEY,
    user_id        INTEGER,
    species_id     INTEGER,
    nickname       TEXT,
    hunger         INTEGER NOT NULL DEFAULT 100,
    happiness      INTEGER NOT NULL DEFAULT 100,
    level          INTEGER NOT NULL DEFAULT 1,
    xp             INTEGER NOT NULL DEFAULT 0,
    is_breeding    INTEGER NOT NULL DEFAULT 0,
    caught_at      TEXT NOT NULL DEFAULT (datetime('now')),
    hunger_alerted INTEGER
);
CREATE TABLE trades (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    proposer_id          INTEGER,
    recipient_id         INTEGER,
    proposer_animal_id   TEXT,
    recipient_animal_id  TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    status               TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE user_achievements (
    user_id         INTEGER,
    achievement_key TEXT,
    earned_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, achievement_key)
);
CREATE TABLE prompt_responses (
    group_chat_id  INTEGER,
    prompt_sent_at TEXT,
    user_id        INTEGER,
    PRIMARY KEY (group_chat_id, prompt_sent_at, user_id)
);
CREATE TABLE wild_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    group_chat_id     INTEGER,
    species_id        INTEGER,
    message_id        INTEGER,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    caught_by_user_id INTEGER
);
CREATE TABLE user_purchases (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER,
    item_key     TEXT,
    purchased_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE user_enclosures (
    user_id INTEGER,
    habitat TEXT NOT NULL,
    level   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, habitat)
);
"""


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    monkeypatch.setattr("db.DATABASE_PATH", path)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO species (name, emoji, rarity, catch_rate, catch_cost, habitat) "
        "VALUES ('Mouse', '🐭', 'common', 0.8, 20, 'woodland')"
    )
    conn.execute(
        "INSERT INTO users (user_id, username, group_chat_id, coins) VALUES (1, 'alice', -100, 500)"
    )
    conn.execute(
        "INSERT INTO users (user_id, username, group_chat_id, coins) VALUES (2, 'bob', -100, 200)"
    )
    conn.commit()
    conn.close()
    yield path


def _sid(db_env):
    return db.get_all_species()[0]["species_id"]


# ── get_animal_by_position: 1-based indexing ──────────────────────────────────


def test_get_animal_by_position(db_env):
    sid = _sid(db_env)
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 1, sid)
    assert db.get_animal_by_position(1, 1)["animal_id"] == "a1"
    assert db.get_animal_by_position(1, 2)["animal_id"] == "a2"
    assert db.get_animal_by_position(1, 99) is None


# ── award_achievement: INSERT OR IGNORE deduplication ────────────────────────


def test_award_achievement_no_duplicates(db_env):
    db.award_achievement(1, "first_catch")
    db.award_achievement(1, "first_catch")
    assert len(db.get_user_achievements(1)) == 1


# ── resolve_trade: atomic double owner swap ───────────────────────────────────


def test_resolve_trade_accepted_swaps_owners(db_env):
    sid = _sid(db_env)
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 2, sid)
    trade_id = db.create_trade(1, 2, "a1", "a2")
    db.resolve_trade(trade_id, "accepted")
    assert db.get_animal("a1")["user_id"] == 2
    assert db.get_animal("a2")["user_id"] == 1
    assert db.get_trade(trade_id)["status"] == "accepted"


def test_resolve_trade_declined_does_not_swap(db_env):
    sid = _sid(db_env)
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 2, sid)
    trade_id = db.create_trade(1, 2, "a1", "a2")
    db.resolve_trade(trade_id, "declined")
    assert db.get_animal("a1")["user_id"] == 1
    assert db.get_animal("a2")["user_id"] == 2
    assert db.get_trade(trade_id)["status"] == "declined"


# ── prompt responses: INSERT OR IGNORE + full-group check ────────────────────


def test_record_prompt_response_no_duplicate(db_env):
    ts = "2026-01-01T00:00:00"
    assert db.record_prompt_response(-100, ts, 1) is True
    assert db.record_prompt_response(-100, ts, 1) is False


def test_all_group_members_checked_in(db_env):
    ts = "2026-01-01T00:00:00"
    assert not db.all_group_members_checked_in(-100, ts)
    db.record_prompt_response(-100, ts, 1)
    assert not db.all_group_members_checked_in(-100, ts)
    db.record_prompt_response(-100, ts, 2)
    assert db.all_group_members_checked_in(-100, ts)


# ── collect_enclosure_coins: read-then-reset ─────────────────────────────────


def test_collect_enclosure_coins(db_env):
    db.add_pending_enclosure_coins(1, 75)
    claimed = db.collect_enclosure_coins(1)
    assert claimed == 75
    assert db.get_pending_enclosure_coins(1) == 0


def test_collect_enclosure_coins_returns_zero_when_empty(db_env):
    assert db.collect_enclosure_coins(1) == 0


# ── coin rounding: all writes produce whole numbers ──────────────────────────


def test_add_coins_with_float_stores_integer(db_env):
    initial = db.get_user(1)["coins"]
    db.add_coins(1, 12.7)
    result = db.get_user(1)["coins"]
    assert result == round(initial + 12.7)
    assert isinstance(result, int)


def test_add_pending_enclosure_coins_with_float_stores_integer(db_env):
    db.add_pending_enclosure_coins(1, 35.6)
    pending = db.get_pending_enclosure_coins(1)
    assert pending == 36
    assert isinstance(pending, int)


def test_collect_enclosure_coins_rounds_legacy_float_in_db(db_env):
    """Simulate a DB row with a legacy float in pending_enclosure_coins."""
    import sqlite3

    conn = sqlite3.connect(db_env)
    conn.execute("UPDATE users SET pending_enclosure_coins = 1932.4 WHERE user_id = 1")
    conn.commit()
    conn.close()

    claimed = db.collect_enclosure_coins(1)
    assert claimed == 1932
    assert isinstance(claimed, int)
    coins = db.get_user(1)["coins"]
    assert isinstance(coins, int)
    assert coins == 500 + 1932  # initial 500 + claimed


def test_collect_enclosure_coins_zeroes_pending_after_collect(db_env):
    db.add_pending_enclosure_coins(1, 100)
    db.collect_enclosure_coins(1)
    assert db.get_pending_enclosure_coins(1) == 0


# ── claim_wild_event: atomic first-one-wins ───────────────────────────────────


def test_claim_wild_event_first_wins(db_env):
    sid = _sid(db_env)
    event_id = db.create_wild_event(-100, sid, 999)
    assert db.claim_wild_event(event_id, 1) is True
    assert db.claim_wild_event(event_id, 2) is False


# ── get_item_counts: GROUP BY aggregation ───────────────────────────────


def test_get_item_counts(db_env):
    db.record_purchase(1, "mega_feed")
    db.record_purchase(1, "mega_feed")
    db.record_purchase(1, "lucky_token")
    counts = db.get_item_counts(1)
    assert counts["mega_feed"] == 2
    assert counts["lucky_token"] == 1
    assert counts.get("breed_boost", 0) == 0
