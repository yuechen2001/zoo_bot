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
    from migrate import run_migrations

    run_migrations(DATABASE_PATH)
    with get_conn() as conn:
        _seed_species(conn)


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


# ── Group state ───────────────────────────────────────────────────────────────


def get_group_state(group_chat_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM group_state WHERE group_chat_id = ?", (group_chat_id,)
        ).fetchone()


def set_group_last_prompt(group_chat_id: int, timestamp: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO group_state (group_chat_id, last_prompt_at) VALUES (?, ?) "
            "ON CONFLICT(group_chat_id) DO UPDATE SET last_prompt_at = excluded.last_prompt_at",
            (group_chat_id, timestamp),
        )


def set_autofeed(user_id: int, threshold: int | None, max_coins: int | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET autofeed_threshold = ?, autofeed_max_coins = ? WHERE user_id = ?",
            (threshold, max_coins, user_id),
        )


def get_autofeed_users() -> list:
    """Users with autofeed enabled who have a group chat."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE autofeed_threshold IS NOT NULL AND group_chat_id IS NOT NULL"
        ).fetchall()


def get_animals_below_hunger(user_id: int, threshold: int) -> list:
    """Non-breeding animals below threshold, sorted by hunger ascending."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.*, s.name AS species_name, s.emoji, s.rarity, s.hunger_decay "
            "FROM animals a JOIN species s ON s.species_id = a.species_id "
            "WHERE a.user_id = ? AND a.hunger < ? AND a.is_breeding = 0 "
            "ORDER BY a.hunger ASC",
            (user_id, threshold),
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


def get_ready_breeds(reminder_minutes: int = 30):
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
            "WHERE bq.collected = 0 AND datetime(bq.ready_at) <= datetime('now') "
            "AND (bq.last_notified_at IS NULL "
            "     OR datetime(bq.last_notified_at) <= datetime('now', ? || ' minutes'))",
            (f"-{reminder_minutes}",),
        ).fetchall()


def mark_breed_notified(breed_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE breeding_queue SET last_notified_at = datetime('now') WHERE id = ?",
            (breed_id,),
        )


def get_active_breed(user_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT bq.*, "
            "sa.emoji AS emoji_a, sa.name AS name_a, "
            "sb.emoji AS emoji_b, sb.name AS name_b "
            "FROM breeding_queue bq "
            "JOIN animals pa ON pa.animal_id = bq.parent_a "
            "JOIN species sa ON sa.species_id = pa.species_id "
            "JOIN animals pb ON pb.animal_id = bq.parent_b "
            "JOIN species sb ON sb.species_id = pb.species_id "
            "WHERE bq.user_id = ? AND bq.collected = 0",
            (user_id,),
        ).fetchone()


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
            now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
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
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=TRADE_EXPIRY_MINUTES)
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


def has_prompt_response(group_chat_id: int, prompt_sent_at: str, user_id: int) -> bool:
    """True if this user already responded to the given prompt."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM prompt_responses WHERE group_chat_id = ? AND prompt_sent_at = ? AND user_id = ?",
            (group_chat_id, prompt_sent_at, user_id),
        ).fetchone()
    return row is not None


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
