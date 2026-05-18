"""
Direct tests for db.py functions against a real temp SQLite DB.
Handler tests mock db.* entirely, so these tests ensure the actual SQL is correct.
"""

import datetime
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
    animal_id   TEXT PRIMARY KEY,
    user_id     INTEGER,
    species_id  INTEGER,
    nickname    TEXT,
    hunger      INTEGER NOT NULL DEFAULT 100,
    happiness   INTEGER NOT NULL DEFAULT 100,
    level       INTEGER NOT NULL DEFAULT 1,
    xp          INTEGER NOT NULL DEFAULT 0,
    is_breeding INTEGER NOT NULL DEFAULT 0,
    caught_at   TEXT NOT NULL DEFAULT (datetime('now')),
    hunger_alerted INTEGER
);
CREATE TABLE breeding_queue (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER,
    parent_a             TEXT,
    parent_b             TEXT,
    offspring_species_id INTEGER,
    ready_at             TEXT NOT NULL,
    collected            INTEGER NOT NULL DEFAULT 0,
    last_notified_at     TEXT
);
CREATE TABLE group_state (
    group_chat_id INTEGER PRIMARY KEY,
    last_prompt_at TEXT
);
CREATE TABLE user_achievements (
    user_id         INTEGER,
    achievement_key TEXT,
    earned_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, achievement_key)
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
CREATE TABLE prompt_responses (
    group_chat_id  INTEGER,
    prompt_sent_at TEXT,
    user_id        INTEGER,
    PRIMARY KEY (group_chat_id, prompt_sent_at, user_id)
);
CREATE TABLE investments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER,
    amount        INTEGER,
    return_amount INTEGER,
    invested_at   TEXT NOT NULL DEFAULT (datetime('now')),
    collected     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE user_enclosures (
    user_id INTEGER,
    habitat TEXT NOT NULL,
    level   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, habitat)
);
CREATE TABLE wild_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    group_chat_id       INTEGER,
    species_id          INTEGER,
    message_id          INTEGER,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    caught_by_user_id   INTEGER
);
CREATE TABLE user_purchases (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER,
    item_key     TEXT,
    purchased_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE bot_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE trivia_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER,
    asked_at  TEXT NOT NULL
);
CREATE TABLE daily_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    claimed_at  TEXT NOT NULL
);
"""


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    monkeypatch.setattr("db.DATABASE_PATH", path)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO species (name, emoji, rarity, catch_rate, catch_cost, hunger_decay, breed_time_hrs, habitat) "
        "VALUES ('Mouse', '🐭', 'common', 0.8, 20, 5, 24, 'woodland')"
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


# ── Users ─────────────────────────────────────────────────────────────────────


def test_get_users_in_group(db_env):
    users = db.get_users_in_group(-100)
    assert len(users) == 2
    assert {u["username"] for u in users} == {"alice", "bob"}


def test_get_users_in_group_excludes_paused(db_env):
    future = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(hours=1)
    ).isoformat()
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET paused_until = ? WHERE user_id = 1", (future,))
    users = db.get_users_in_group(-100)
    assert len(users) == 1
    assert users[0]["username"] == "bob"


def test_get_all_active_users(db_env):
    users = db.get_all_active_users()
    assert len(users) == 2


def test_get_all_active_users_excludes_opted_out(db_env):
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET opted_in = 0 WHERE user_id = 1")
    users = db.get_all_active_users()
    assert len(users) == 1


# ── Group state ───────────────────────────────────────────────────────────────


def test_set_and_get_group_state(db_env):
    assert db.get_group_state(-100) is None
    db.set_group_last_prompt(-100, "2026-01-01T00:00:00")
    state = db.get_group_state(-100)
    assert state["last_prompt_at"] == "2026-01-01T00:00:00"


def test_set_group_last_prompt_upserts(db_env):
    db.set_group_last_prompt(-100, "2026-01-01T00:00:00")
    db.set_group_last_prompt(-100, "2026-01-02T00:00:00")
    assert db.get_group_state(-100)["last_prompt_at"] == "2026-01-02T00:00:00"


# ── Autofeed ──────────────────────────────────────────────────────────────────


def test_set_autofeed_and_get_autofeed_users(db_env):
    assert db.get_autofeed_users() == []
    db.set_autofeed(1, threshold=30, max_coins=50)
    users = db.get_autofeed_users()
    assert len(users) == 1
    assert users[0]["autofeed_threshold"] == 30


def test_set_autofeed_disable(db_env):
    db.set_autofeed(1, threshold=30, max_coins=50)
    db.set_autofeed(1, threshold=None, max_coins=None)
    assert db.get_autofeed_users() == []


# ── Species ───────────────────────────────────────────────────────────────────


def test_get_species(db_env):
    species = db.get_all_species()
    assert len(species) == 1
    row = db.get_species(species[0]["species_id"])
    assert row["name"] == "Mouse"


def test_get_species_by_rarity(db_env):
    rows = db.get_species_by_rarity("common")
    assert len(rows) == 1
    assert db.get_species_by_rarity("legendary") == []


def test_get_species_habitat(db_env):
    sid = db.get_all_species()[0]["species_id"]
    assert db.get_species_habitat(sid) == "woodland"
    assert db.get_species_habitat(99999) == "woodland"  # fallback


# ── Animals ───────────────────────────────────────────────────────────────────


def test_add_and_get_animal(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    animal = db.get_animal("a1")
    assert animal["animal_id"] == "a1"
    assert animal["user_id"] == 1


def test_get_animal_by_position(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 1, sid)
    assert db.get_animal_by_position(1, 1)["animal_id"] == "a1"
    assert db.get_animal_by_position(1, 2)["animal_id"] == "a2"
    assert db.get_animal_by_position(1, 99) is None


def test_transfer_animal(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.transfer_animal("a1", 2)
    assert db.get_animal("a1")["user_id"] == 2


def test_delete_animal(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.delete_animal("a1")
    assert db.get_animal("a1") is None


def test_reset_hunger_alerted(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    with db.get_conn() as conn:
        conn.execute("UPDATE animals SET hunger_alerted = 20 WHERE animal_id = 'a1'")
    db.reset_hunger_alerted("a1")
    assert db.get_animal("a1")["hunger_alerted"] is None


def test_get_animals_below_hunger(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    with db.get_conn() as conn:
        conn.execute("UPDATE animals SET hunger = 15 WHERE animal_id = 'a1'")
    low = db.get_animals_below_hunger(1, 30)
    assert len(low) == 1
    assert low[0]["animal_id"] == "a1"


def test_get_owned_species_ids(db_env):
    sid = db.get_all_species()[0]["species_id"]
    assert db.get_owned_species_ids(1) == set()
    db.add_animal("a1", 1, sid)
    assert db.get_owned_species_ids(1) == {sid}


# ── Breeding ──────────────────────────────────────────────────────────────────


def test_get_pending_breed(db_env):
    assert db.get_pending_breed(1) is None
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 1, sid)
    ready = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(hours=2)
    ).isoformat()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO breeding_queue (user_id, parent_a, parent_b, offspring_species_id, ready_at) "
            "VALUES (1, 'a1', 'a2', ?, ?)",
            (sid, ready),
        )
    assert db.get_pending_breed(1) is not None


def test_get_active_breed(db_env):
    assert db.get_active_breed(1) is None
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 1, sid)
    ready = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(hours=2)
    ).isoformat()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO breeding_queue (user_id, parent_a, parent_b, offspring_species_id, ready_at) "
            "VALUES (1, 'a1', 'a2', ?, ?)",
            (sid, ready),
        )
    breed = db.get_active_breed(1)
    assert breed is not None
    assert breed["name_a"] == "Mouse"


# ── Achievements ──────────────────────────────────────────────────────────────


def test_award_and_get_achievements(db_env):
    assert db.get_user_achievements(1) == []
    db.award_achievement(1, "first_catch")
    rows = db.get_user_achievements(1)
    assert len(rows) == 1
    assert rows[0]["achievement_key"] == "first_catch"


def test_get_achievement_keys(db_env):
    db.award_achievement(1, "first_catch")
    db.award_achievement(1, "zoo_10")
    assert db.get_achievement_keys(1) == {"first_catch", "zoo_10"}


def test_award_achievement_no_duplicates(db_env):
    db.award_achievement(1, "first_catch")
    db.award_achievement(1, "first_catch")
    assert len(db.get_user_achievements(1)) == 1


# ── Trades ────────────────────────────────────────────────────────────────────


def test_create_get_trade(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 2, sid)
    trade_id = db.create_trade(1, 2, "a1", "a2")
    trade = db.get_trade(trade_id)
    assert trade["proposer_id"] == 1
    assert trade["status"] == "pending"


def test_get_user_by_username(db_env):
    user = db.get_user_by_username("alice")
    assert user["user_id"] == 1
    assert db.get_user_by_username("nobody") is None


def test_has_pending_trade_for_animal(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 2, sid)
    assert not db.has_pending_trade_for_animal("a1")
    db.create_trade(1, 2, "a1", "a2")
    assert db.has_pending_trade_for_animal("a1")
    assert db.has_pending_trade_for_animal("a2")


def test_resolve_trade_accepted(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 2, sid)
    trade_id = db.create_trade(1, 2, "a1", "a2")
    db.resolve_trade(trade_id, "accepted")
    assert db.get_animal("a1")["user_id"] == 2
    assert db.get_animal("a2")["user_id"] == 1
    assert db.get_trade(trade_id)["status"] == "accepted"


def test_resolve_trade_declined(db_env):
    sid = db.get_all_species()[0]["species_id"]
    db.add_animal("a1", 1, sid)
    db.add_animal("a2", 2, sid)
    trade_id = db.create_trade(1, 2, "a1", "a2")
    db.resolve_trade(trade_id, "declined")
    assert db.get_animal("a1")["user_id"] == 1  # unchanged
    assert db.get_trade(trade_id)["status"] == "declined"


# ── Prompt responses ──────────────────────────────────────────────────────────


def test_record_and_has_prompt_response(db_env):
    assert not db.has_prompt_response(-100, "2026-01-01T00:00:00", 1)
    result = db.record_prompt_response(-100, "2026-01-01T00:00:00", 1)
    assert result is True
    assert db.has_prompt_response(-100, "2026-01-01T00:00:00", 1)


def test_record_prompt_response_no_duplicate(db_env):
    db.record_prompt_response(-100, "2026-01-01T00:00:00", 1)
    result = db.record_prompt_response(-100, "2026-01-01T00:00:00", 1)
    assert result is False


def test_all_group_members_checked_in(db_env):
    ts = "2026-01-01T00:00:00"
    assert not db.all_group_members_checked_in(-100, ts)
    db.record_prompt_response(-100, ts, 1)
    assert not db.all_group_members_checked_in(-100, ts)
    db.record_prompt_response(-100, ts, 2)
    assert db.all_group_members_checked_in(-100, ts)


# ── Investments ───────────────────────────────────────────────────────────────


def test_create_and_get_active_investment(db_env):
    assert db.get_active_investment(1) is None
    db.create_investment(1, 100, 125)
    inv = db.get_active_investment(1)
    assert inv["amount"] == 100
    assert inv["return_amount"] == 125


def test_collect_investment(db_env):
    db.create_investment(1, 100, 125)
    inv = db.get_active_investment(1)
    db.collect_investment(inv["id"])
    assert db.get_active_investment(1) is None


# ── Wild events ───────────────────────────────────────────────────────────────


def test_create_and_get_wild_event(db_env):
    sid = db.get_all_species()[0]["species_id"]
    event_id = db.create_wild_event(-100, sid, 999)
    event = db.get_wild_event(event_id)
    assert event["group_chat_id"] == -100
    assert event["caught_by_user_id"] is None


def test_claim_wild_event(db_env):
    sid = db.get_all_species()[0]["species_id"]
    event_id = db.create_wild_event(-100, sid, 999)
    assert db.claim_wild_event(event_id, 1) is True
    assert db.claim_wild_event(event_id, 2) is False  # already claimed


def test_get_expired_wild_events(db_env):
    sid = db.get_all_species()[0]["species_id"]
    event_id = db.create_wild_event(-100, sid, 999)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE wild_events SET created_at = datetime('now', '-10 minutes') WHERE id = ?",
            (event_id,),
        )
    expired = db.get_expired_wild_events(expiry_minutes=5)
    assert len(expired) == 1
    assert expired[0]["id"] == event_id


# ── Enclosure coins ───────────────────────────────────────────────────────────


def test_add_and_collect_enclosure_coins(db_env):
    assert db.get_pending_enclosure_coins(1) == 0
    db.add_pending_enclosure_coins(1, 50)
    assert db.get_pending_enclosure_coins(1) == 50
    claimed = db.collect_enclosure_coins(1)
    assert claimed == 50
    assert db.get_pending_enclosure_coins(1) == 0


def test_collect_enclosure_coins_zero(db_env):
    assert db.collect_enclosure_coins(1) == 0


# ── Store ─────────────────────────────────────────────────────────────────────


def test_record_and_has_purchased(db_env):
    assert not db.has_purchased(1, "mega_feed")
    db.record_purchase(1, "mega_feed")
    assert db.has_purchased(1, "mega_feed")


def test_get_consumable_counts(db_env):
    db.record_purchase(1, "mega_feed")
    db.record_purchase(1, "mega_feed")
    db.record_purchase(1, "lucky_token")
    counts = db.get_consumable_counts(1)
    assert counts["mega_feed"] == 2
    assert counts["lucky_token"] == 1


def test_set_active_title(db_env):
    db.set_active_title(1, "title_keeper")
    assert db.get_user(1)["active_title"] == "title_keeper"
    db.set_active_title(1, None)
    assert db.get_user(1)["active_title"] is None


def test_set_lucky_catch(db_env):
    db.set_lucky_catch(1, True)
    assert db.get_user(1)["lucky_catch_active"] == 1
    db.set_lucky_catch(1, False)
    assert db.get_user(1)["lucky_catch_active"] == 0


def test_set_mood_booster(db_env):
    db.set_mood_booster(1, True)
    assert db.get_user(1)["mood_booster_active"] == 1


def test_set_catch_net(db_env):
    db.set_catch_net(1, True)
    assert db.get_user(1)["catch_net_active"] == 1


# ── Bot settings ──────────────────────────────────────────────────────────────


def test_set_and_get_setting(db_env):
    assert db.get_setting("some_key") is None
    db.set_setting("some_key", "some_value")
    assert db.get_setting("some_key") == "some_value"


def test_set_setting_upserts(db_env):
    db.set_setting("k", "v1")
    db.set_setting("k", "v2")
    assert db.get_setting("k") == "v2"


# ── Active group chats ────────────────────────────────────────────────────────


def test_get_active_group_chats(db_env):
    chats = db.get_active_group_chats()
    assert -100 in chats
