import datetime
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
        conn.executescript(
            """
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

            CREATE TABLE IF NOT EXISTS trades (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                proposer_id         INTEGER NOT NULL REFERENCES users(user_id),
                recipient_id        INTEGER NOT NULL REFERENCES users(user_id),
                proposer_animal_id  TEXT NOT NULL REFERENCES animals(animal_id),
                recipient_animal_id TEXT NOT NULL REFERENCES animals(animal_id),
                created_at          TEXT DEFAULT (datetime('now')),
                status              TEXT NOT NULL DEFAULT 'pending'
            );
        """
        )
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS prompt_responses (
                group_chat_id INTEGER NOT NULL,
                prompt_sent_at TEXT NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                PRIMARY KEY (group_chat_id, prompt_sent_at, user_id)
            );
            """
        )
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS investments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER REFERENCES users(user_id),
                amount       INTEGER NOT NULL,
                return_amount INTEGER NOT NULL,
                invested_at  TEXT DEFAULT (datetime('now')),
                collected    INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_enclosures (
                user_id  INTEGER REFERENCES users(user_id),
                habitat  TEXT NOT NULL,
                level    INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, habitat)
            );
            """
        )
        # Add new columns to existing tables (idempotent)
        for stmt in [
            "ALTER TABLE animals ADD COLUMN hunger_alerted INTEGER DEFAULT NULL",
            "ALTER TABLE species ADD COLUMN habitat TEXT",
        ]:
            try:
                conn.execute(stmt)
            except Exception:
                pass
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
                "UPDATE species SET catch_rate=?, catch_cost=?, hunger_decay=?, breed_time_hrs=?, habitat=? WHERE species_id=?",
                (
                    s["catch_rate"],
                    s["catch_cost"],
                    s["hunger_decay"],
                    s["breed_time_hrs"],
                    s["habitat"],
                    existing["species_id"],
                ),
            )
        else:
            conn.execute(
                "INSERT INTO species (name, emoji, rarity, catch_rate, catch_cost, hunger_decay, breed_time_hrs, habitat) "
                "VALUES (:name, :emoji, :rarity, :catch_rate, :catch_cost, :hunger_decay, :breed_time_hrs, :habitat)",
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
            "SELECT DISTINCT u.* FROM users u " "JOIN animals a ON a.user_id = u.user_id"
        ).fetchall()


# ── Species ───────────────────────────────────────────────────────────────────


def get_species(species_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM species WHERE species_id = ?", (species_id,)).fetchone()


def get_species_by_rarity(rarity):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM species WHERE rarity = ?", (rarity,)).fetchall()


def get_all_species():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM species").fetchall()


def get_owned_species_ids(user_id: int) -> set:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT species_id FROM animals WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {r["species_id"] for r in rows}


# ── Animals ───────────────────────────────────────────────────────────────────


def get_animals(user_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.*, s.name AS species_name, s.emoji, s.rarity, s.hunger_decay, s.catch_cost, s.habitat "
            "FROM animals a JOIN species s ON s.species_id = a.species_id "
            "WHERE a.user_id = ? ORDER BY a.caught_at",
            (user_id,),
        ).fetchall()


def get_animal(animal_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.*, s.name AS species_name, s.emoji, s.rarity, s.hunger_decay, s.breed_time_hrs, s.habitat "
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


# ── Trades ────────────────────────────────────────────────────────────────────


def get_user_by_username(username: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def create_trade(proposer_id, recipient_id, proposer_animal_id, recipient_animal_id) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO trades (proposer_id, recipient_id, proposer_animal_id, recipient_animal_id) "
            "VALUES (?, ?, ?, ?)",
            (proposer_id, recipient_id, proposer_animal_id, recipient_animal_id),
        )
        return cur.lastrowid


def get_trade(trade_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()


def has_pending_trade_for_animal(animal_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM trades WHERE status = 'pending' "
            "AND (proposer_animal_id = ? OR recipient_animal_id = ?)",
            (animal_id, animal_id),
        ).fetchone()
        return row is not None


def resolve_trade(trade_id: int, status: str):
    """Finalise a trade. For 'accepted', atomically swap the two animals' owners."""
    with get_conn() as conn:
        trade = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
        if status == "accepted":
            now_str = datetime.datetime.utcnow().isoformat()
            conn.execute(
                "UPDATE animals SET user_id = ?, caught_at = ? WHERE animal_id = ?",
                (trade["recipient_id"], now_str, trade["proposer_animal_id"]),
            )
            conn.execute(
                "UPDATE animals SET user_id = ?, caught_at = ? WHERE animal_id = ?",
                (trade["proposer_id"], now_str, trade["recipient_animal_id"]),
            )
        conn.execute("UPDATE trades SET status = ? WHERE id = ?", (status, trade_id))


def expire_old_trades() -> list:
    """Mark pending trades older than TRADE_EXPIRY_MINUTES as expired. Returns the affected rows."""
    from config import TRADE_EXPIRY_MINUTES

    cutoff = (
        datetime.datetime.utcnow() - datetime.timedelta(minutes=TRADE_EXPIRY_MINUTES)
    ).isoformat()
    with get_conn() as conn:
        expired = conn.execute(
            "SELECT * FROM trades WHERE status = 'pending' AND created_at < ?",
            (cutoff,),
        ).fetchall()
        if expired:
            conn.execute(
                "UPDATE trades SET status = 'expired' WHERE status = 'pending' AND created_at < ?",
                (cutoff,),
            )
    return expired


def record_prompt_response(group_chat_id: int, prompt_sent_at: str, user_id: int) -> bool:
    """Insert a prompt response. Returns True if inserted (first response), False if duplicate."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO prompt_responses (group_chat_id, prompt_sent_at, user_id) "
            "VALUES (?, ?, ?)",
            (group_chat_id, prompt_sent_at, user_id),
        )
    return cur.rowcount == 1


def all_group_members_checked_in(group_chat_id: int, prompt_time_str: str) -> bool:
    """True if every opted-in, non-paused member of the group has responded to this prompt."""
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM users WHERE group_chat_id = ? AND opted_in = 1 "
            "AND (paused_until IS NULL OR paused_until < datetime('now'))",
            (group_chat_id,),
        ).fetchone()[0]
        if not total:
            return False
        responded = conn.execute(
            "SELECT COUNT(*) FROM prompt_responses "
            "WHERE group_chat_id = ? AND prompt_sent_at = ?",
            (group_chat_id, prompt_time_str),
        ).fetchone()[0]
    return responded >= total


# ── Animals (extra helpers) ───────────────────────────────────────────────────


def delete_animal(animal_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM animals WHERE animal_id = ?", (animal_id,))


def reset_hunger_alerted(animal_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE animals SET hunger_alerted = NULL WHERE animal_id = ?", (animal_id,))


def get_low_hunger_animals():
    """Animals with hunger ≤ 20 that need an alert, joined with owner group_chat_id."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.animal_id, a.user_id, a.nickname, a.hunger, a.hunger_alerted, "
            "s.name, s.emoji, u.group_chat_id "
            "FROM animals a "
            "JOIN species s ON s.species_id = a.species_id "
            "JOIN users u ON u.user_id = a.user_id "
            "WHERE a.hunger <= 20 AND a.is_breeding = 0",
        ).fetchall()


# ── Investments ───────────────────────────────────────────────────────────────


def get_active_investment(user_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM investments WHERE user_id = ? AND collected = 0",
            (user_id,),
        ).fetchone()


def create_investment(user_id: int, amount: int, return_amount: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO investments (user_id, amount, return_amount) VALUES (?, ?, ?)",
            (user_id, amount, return_amount),
        )


def collect_investment(investment_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE investments SET collected = 1 WHERE id = ?", (investment_id,))


# ── Coins (general) ───────────────────────────────────────────────────────────


def add_coins(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))


# ── Enclosures ────────────────────────────────────────────────────────────────


def give_starter_enclosures(user_id: int):
    from species_data import HABITATS

    with get_conn() as conn:
        for habitat in HABITATS:
            conn.execute(
                "INSERT OR IGNORE INTO user_enclosures (user_id, habitat, level) VALUES (?, ?, 1)",
                (user_id, habitat),
            )


def get_enclosures(user_id: int) -> dict:
    """Return {habitat: level} for all enclosures the user owns."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT habitat, level FROM user_enclosures WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {r["habitat"]: r["level"] for r in rows}


def get_enclosure_level(user_id: int, habitat: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT level FROM user_enclosures WHERE user_id = ? AND habitat = ?",
            (user_id, habitat),
        ).fetchone()
    return row["level"] if row else 1


def get_animal_count_by_habitat(user_id: int, habitat: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM animals a "
            "JOIN species s ON s.species_id = a.species_id "
            "WHERE a.user_id = ? AND s.habitat = ?",
            (user_id, habitat),
        ).fetchone()
    return row["cnt"] if row else 0


def get_species_habitat(species_id: int) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT habitat FROM species WHERE species_id = ?", (species_id,)
        ).fetchone()
    return row["habitat"] if row else "woodland"


def upgrade_enclosure(user_id: int, habitat: str) -> str:
    """Increment enclosure level and deduct upgrade cost atomically.

    Returns 'ok', 'max_level', or 'insufficient_coins'.
    """
    from species_data import ENCLOSURE_LEVELS, MAX_ENCLOSURE_LEVEL

    with get_conn() as conn:
        row = conn.execute(
            "SELECT level FROM user_enclosures WHERE user_id = ? AND habitat = ?",
            (user_id, habitat),
        ).fetchone()
        current = row["level"] if row else 1
        if current >= MAX_ENCLOSURE_LEVEL:
            return "max_level"
        cost = ENCLOSURE_LEVELS[current + 1]["upgrade_cost"]
        user = conn.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user or user["coins"] < cost:
            return "insufficient_coins"
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, user_id))
        conn.execute(
            "INSERT INTO user_enclosures (user_id, habitat, level) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, habitat) DO UPDATE SET level = level + 1",
            (user_id, habitat, 2),
        )
    return "ok"
