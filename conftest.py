import sqlite3
import pytest
from game.species_data import SPECIES


class FakeRow(dict):
    """Mimics sqlite3.Row: supports key access but raises on .get() to catch the common bug."""

    def get(self, *args, **kwargs):
        raise AttributeError("sqlite3.Row has no .get() — use row['key'] instead")


def make_row(**kwargs) -> FakeRow:
    """Factory for FakeRow. Use instead of plain dicts when mocking db results in handler tests."""
    return FakeRow(kwargs)


@pytest.fixture
def conn():
    """In-memory SQLite DB with schema + species seeded. Used by game logic tests."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """
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
        CREATE TABLE user_enclosures (
            user_id  INTEGER,
            habitat  TEXT NOT NULL,
            level    INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (user_id, habitat)
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
            massage_active_until    TEXT
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
            is_shiny    INTEGER NOT NULL DEFAULT 0
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
        CREATE TABLE bot_settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE visit_feeds (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id  INTEGER NOT NULL,
            host_id     INTEGER NOT NULL,
            fed_at      TEXT NOT NULL
        );
        CREATE TABLE group_trivia (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            group_chat_id INTEGER NOT NULL,
            correct_answer TEXT NOT NULL,
            fired_at      TEXT NOT NULL,
            expires_at    TEXT NOT NULL,
            message_id    INTEGER,
            resolved      INTEGER NOT NULL DEFAULT 0,
            answered_by   INTEGER
        );
    """
    )
    for s in SPECIES:
        c.execute(
            "INSERT INTO species (name, emoji, rarity, catch_rate, catch_cost, hunger_decay, breed_time_hrs, habitat) "
            "VALUES (:name, :emoji, :rarity, :catch_rate, :catch_cost, :hunger_decay, :breed_time_hrs, :habitat)",
            s,
        )
    c.commit()
    yield c
    c.close()
