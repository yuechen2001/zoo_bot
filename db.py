import sqlite3
from config import DATABASE_PATH
from species_data import SPECIES


def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
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
                breed_time_hrs INTEGER NOT NULL DEFAULT 24
            );

            CREATE TABLE IF NOT EXISTS animals (
                animal_id   TEXT PRIMARY KEY,
                user_id     INTEGER REFERENCES users(user_id),
                species_id  INTEGER REFERENCES species(species_id),
                nickname    TEXT,
                hunger      INTEGER NOT NULL DEFAULT 100,
                happiness   INTEGER NOT NULL DEFAULT 100,
                level       INTEGER NOT NULL DEFAULT 1,
                xp          INTEGER NOT NULL DEFAULT 0,
                is_breeding INTEGER NOT NULL DEFAULT 0,
                caught_at   TEXT DEFAULT (datetime('now'))
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
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER REFERENCES users(user_id),
                asked_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER REFERENCES users(user_id),
                claimed_at  TEXT NOT NULL
            );
        """)
        _seed_species(conn)
        # Backfill any animals that have no nickname with their species name
        conn.execute(
            "UPDATE animals SET nickname = (SELECT name FROM species WHERE species_id = animals.species_id) "
            "WHERE nickname IS NULL OR nickname = ''"
        )


def _seed_species(conn):
    for s in SPECIES:
        existing = conn.execute(
            "SELECT species_id FROM species WHERE name = ? AND emoji = ?",
            (s["name"], s["emoji"]),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE species SET catch_rate=?, catch_cost=?, hunger_decay=?, breed_time_hrs=? WHERE species_id=?",
                (s["catch_rate"], s["catch_cost"], s["hunger_decay"], s["breed_time_hrs"], existing["species_id"]),
            )
        else:
            conn.execute(
                "INSERT INTO species (name, emoji, rarity, catch_rate, catch_cost, hunger_decay, breed_time_hrs) "
                "VALUES (:name, :emoji, :rarity, :catch_rate, :catch_cost, :hunger_decay, :breed_time_hrs)",
                s,
            )


# ── Users ─────────────────────────────────────────────────────────────────────

def get_user(user_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def ensure_user(user_id, username, group_chat_id):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, group_chat_id) VALUES (?, ?, ?)",
            (user_id, username, group_chat_id),
        )
        conn.execute(
            "UPDATE users SET username = ?, group_chat_id = ? WHERE user_id = ?",
            (username, group_chat_id, user_id),
        )


def get_users_in_group(group_chat_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE group_chat_id = ? AND opted_in = 1 AND "
            "(paused_until IS NULL OR paused_until < datetime('now'))",
            (group_chat_id,),
        ).fetchall()


def get_all_active_users():
    """All opted-in, non-paused users with a group chat."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE opted_in = 1 AND group_chat_id IS NOT NULL "
            "AND (paused_until IS NULL OR paused_until < datetime('now'))",
        ).fetchall()


def get_all_users_with_animals():
    """All users who have at least one animal (for stat decay)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT DISTINCT u.* FROM users u "
            "JOIN animals a ON a.user_id = u.user_id"
        ).fetchall()


# ── Species ───────────────────────────────────────────────────────────────────

def get_species(species_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM species WHERE species_id = ?", (species_id,)).fetchone()


def get_species_by_rarity(rarity):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM species WHERE rarity = ?", (rarity,)
        ).fetchall()


# ── Animals ───────────────────────────────────────────────────────────────────

def get_animals(user_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.*, s.name AS species_name, s.emoji, s.rarity, s.hunger_decay "
            "FROM animals a JOIN species s ON s.species_id = a.species_id "
            "WHERE a.user_id = ? ORDER BY a.caught_at",
            (user_id,),
        ).fetchall()


def get_animal(animal_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.*, s.name AS species_name, s.emoji, s.rarity, s.hunger_decay, s.breed_time_hrs "
            "FROM animals a JOIN species s ON s.species_id = a.species_id "
            "WHERE a.animal_id = ?",
            (animal_id,),
        ).fetchone()


def get_animal_by_position(user_id, position):
    """1-based position in the user's zoo list."""
    animals = get_animals(user_id)
    if 1 <= position <= len(animals):
        return animals[position - 1]
    return None


def add_animal(animal_id, user_id, species_id, nickname=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO animals (animal_id, user_id, species_id, nickname) VALUES (?, ?, ?, ?)",
            (animal_id, user_id, species_id, nickname),
        )


# ── Breeding ──────────────────────────────────────────────────────────────────

def get_pending_breed(user_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM breeding_queue WHERE user_id = ? AND collected = 0",
            (user_id,),
        ).fetchone()


def get_ready_breeds():
    with get_conn() as conn:
        return conn.execute(
            "SELECT bq.*, u.group_chat_id, "
            "sa.emoji AS emoji_a, sa.name AS name_a, "
            "sb.emoji AS emoji_b, sb.name AS name_b, "
            "so.emoji AS emoji_offspring, so.name AS name_offspring "
            "FROM breeding_queue bq "
            "JOIN users u ON u.user_id = bq.user_id "
            "JOIN animals pa ON pa.animal_id = bq.parent_a "
            "JOIN species sa ON sa.species_id = pa.species_id "
            "JOIN animals pb ON pb.animal_id = bq.parent_b "
            "JOIN species sb ON sb.species_id = pb.species_id "
            "JOIN species so ON so.species_id = bq.offspring_species_id "
            "WHERE bq.collected = 0 AND bq.ready_at <= datetime('now')",
        ).fetchall()


# ── Achievements ──────────────────────────────────────────────────────────────

def get_user_achievements(user_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM user_achievements WHERE user_id = ? ORDER BY earned_at",
            (user_id,),
        ).fetchall()


def get_achievement_keys(user_id) -> set:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT achievement_key FROM user_achievements WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {r["achievement_key"] for r in rows}


def award_achievement(user_id, key):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_achievements (user_id, achievement_key) VALUES (?, ?)",
            (user_id, key),
        )
