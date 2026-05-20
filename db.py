import datetime
import sqlite3
from config import DATABASE_PATH
from game.species_data import SPECIES


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


def get_oldest_group_prompt_at() -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT MIN(last_prompt_at) FROM group_state").fetchone()
        return row[0] if row else None


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


def add_animal(animal_id, user_id, species_id, nickname=None, hunger=100, is_breeding=0):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO animals (animal_id, user_id, species_id, nickname, hunger, is_breeding) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (animal_id, user_id, species_id, nickname, hunger, is_breeding),
        )


def transfer_animal(animal_id: str, new_user_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE animals SET user_id = ?, caught_at = datetime('now') WHERE animal_id = ?",
            (new_user_id, animal_id),
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
            "SELECT bq.*, u.group_chat_id, u.username, "
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


def create_trade(
    proposer_id, recipient_id, proposer_animal_id, recipient_animal_id, created_at=None
) -> int:
    ts = created_at or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO trades (proposer_id, recipient_id, proposer_animal_id, "
            "recipient_animal_id, created_at, status) VALUES (?, ?, ?, ?, ?, 'pending')",
            (proposer_id, recipient_id, proposer_animal_id, recipient_animal_id, ts),
        )
        return cur.lastrowid


def insert_breed_queue_entry(
    user_id: int,
    parent_a: str,
    parent_b: str,
    offspring_species_id: int,
    ready_at: str,
    last_notified_at: str | None = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO breeding_queue "
            "(user_id, parent_a, parent_b, offspring_species_id, ready_at, collected, last_notified_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (user_id, parent_a, parent_b, offspring_species_id, ready_at, last_notified_at),
        )


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


def get_starved_animals():
    """Animals at hunger = 0 that should be removed."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.animal_id, a.user_id, a.nickname, s.name, s.emoji, u.group_chat_id "
            "FROM animals a "
            "JOIN species s ON s.species_id = a.species_id "
            "JOIN users u ON u.user_id = a.user_id "
            "WHERE a.hunger = 0 AND a.is_breeding = 0",
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
    from game.species_data import HABITATS

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


def set_enclosure_level(user_id: int, habitat: str, level: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_enclosures SET level = ? WHERE user_id = ? AND habitat = ?",
            (level, user_id, habitat),
        )


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
    from game.species_data import ENCLOSURE_LEVELS, MAX_ENCLOSURE_LEVEL

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


# ── Wild events ───────────────────────────────────────────────────────────────


def create_wild_event(group_chat_id: int, species_id: int, message_id: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO wild_events (group_chat_id, species_id, message_id) VALUES (?, ?, ?)",
            (group_chat_id, species_id, message_id),
        )
        return cur.lastrowid


def claim_wild_event(event_id: int, user_id: int) -> bool:
    """Atomically claim the event. Returns True if this user got it, False if already claimed."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE wild_events SET caught_by_user_id = ? "
            "WHERE id = ? AND caught_by_user_id IS NULL",
            (user_id, event_id),
        )
        row = conn.execute(
            "SELECT caught_by_user_id FROM wild_events WHERE id = ?", (event_id,)
        ).fetchone()
        return row is not None and row["caught_by_user_id"] == user_id


def get_expired_wild_events(expiry_minutes: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM wild_events WHERE caught_by_user_id IS NULL "
            "AND datetime(created_at) <= datetime('now', ? || ' minutes')",
            (f"-{expiry_minutes}",),
        ).fetchall()


def get_wild_event(event_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM wild_events WHERE id = ?", (event_id,)).fetchone()


# ── Enclosure collect ─────────────────────────────────────────────────────────


def get_pending_enclosure_coins(user_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT pending_enclosure_coins FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["pending_enclosure_coins"] if row else 0


def add_pending_enclosure_coins(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET pending_enclosure_coins = pending_enclosure_coins + ? WHERE user_id = ?",
            (amount, user_id),
        )


def collect_enclosure_coins(user_id: int) -> int:
    """Claim and reset pending enclosure coins. Returns the amount claimed."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT pending_enclosure_coins FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row or row["pending_enclosure_coins"] == 0:
            return 0
        amount = row["pending_enclosure_coins"]
        conn.execute(
            "UPDATE users SET coins = coins + ?, pending_enclosure_coins = 0 WHERE user_id = ?",
            (amount, user_id),
        )
        return amount


# ── Store ─────────────────────────────────────────────────────────────────────


def has_purchased(user_id: int, item_key: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM user_purchases WHERE user_id = ? AND item_key = ?",
            (user_id, item_key),
        ).fetchone()
        return row is not None


def record_purchase(user_id: int, item_key: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_purchases (user_id, item_key) VALUES (?, ?)",
            (user_id, item_key),
        )


def set_active_title(user_id: int, title_key: str | None):
    with get_conn() as conn:
        conn.execute("UPDATE users SET active_title = ? WHERE user_id = ?", (title_key, user_id))


def set_lucky_catch(user_id: int, active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET lucky_catch_active = ? WHERE user_id = ?",
            (1 if active else 0, user_id),
        )


def set_mood_booster(user_id: int, active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET mood_booster_active = ? WHERE user_id = ?",
            (1 if active else 0, user_id),
        )


def set_catch_net(user_id: int, active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET catch_net_active = ? WHERE user_id = ?",
            (1 if active else 0, user_id),
        )


def set_rare_magnet(user_id: int, active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET rare_magnet_active = ? WHERE user_id = ?",
            (1 if active else 0, user_id),
        )


def set_streak_shield(user_id: int, active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET streak_shield_active = ? WHERE user_id = ?",
            (1 if active else 0, user_id),
        )


def set_epic_magnet(user_id: int, active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET epic_magnet_active = ? WHERE user_id = ?",
            (1 if active else 0, user_id),
        )


def get_item_counts(user_id: int) -> dict[str, int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT item_key, COUNT(*) AS n FROM user_purchases WHERE user_id = ? GROUP BY item_key",
            (user_id,),
        ).fetchall()
    return {r["item_key"]: r["n"] for r in rows}


def get_owned_title_keys(user_id: int) -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT item_key FROM user_purchases WHERE user_id = ? AND item_key LIKE 'title_%'",
            (user_id,),
        ).fetchall()
    return {r["item_key"] for r in rows}


def deduct_coins(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, user_id))


def get_oldest_purchase(user_id: int, item_key: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT id FROM user_purchases WHERE user_id = ? AND item_key = ? "
            "ORDER BY purchased_at ASC LIMIT 1",
            (user_id, item_key),
        ).fetchone()


def consume_purchase(purchase_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM user_purchases WHERE id = ?", (purchase_id,))


def feed_animal_and_consume(animal_id: str, purchase_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE animals SET hunger = 100, hunger_alerted = NULL WHERE animal_id = ?",
            (animal_id,),
        )
        conn.execute("DELETE FROM user_purchases WHERE id = ?", (purchase_id,))


def adjust_breed_time_and_consume(breed_id: int, new_ready_at: str, purchase_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE breeding_queue SET ready_at = ? WHERE id = ?",
            (new_ready_at, breed_id),
        )
        conn.execute("DELETE FROM user_purchases WHERE id = ?", (purchase_id,))


# ── User state helpers ────────────────────────────────────────────────────────


def set_opted_in(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET opted_in = 1 WHERE user_id = ?", (user_id,))


def set_opted_out(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET opted_in = 0, consecutive_misses = 0 WHERE user_id = ?", (user_id,)
        )


def set_paused_until(user_id: int, paused_until: str | None) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET paused_until = ? WHERE user_id = ?", (paused_until, user_id))


def update_group_chat_id(user_id: int, group_chat_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET group_chat_id = ? WHERE user_id = ?", (group_chat_id, user_id)
        )


def set_last_prompt_at(user_id: int, now_str: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_prompt_at = ? WHERE user_id = ?", (now_str, user_id))


def record_checkin(user_id: int, emoji: str, coins: int, new_streak: int, now_str: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET streak_windows = ?, consecutive_misses = 0, "
            "coins = coins + ?, last_checkin_at = ? WHERE user_id = ?",
            (new_streak, coins, now_str, user_id),
        )
        conn.execute(
            "INSERT INTO mood_checkins (user_id, emoji, coins_earned, streak_window) "
            "VALUES (?, ?, ?, ?)",
            (user_id, emoji, coins, new_streak),
        )


# ── Massage ───────────────────────────────────────────────────────────────────


def activate_massage(user_id: int, cost: int, massage_until: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = coins - ?, massage_active_until = ? WHERE user_id = ?",
            (cost, massage_until, user_id),
        )


# ── Feed ──────────────────────────────────────────────────────────────────────


def feed_animal(user_id: int, animal_id: str, new_hunger: int, feed_cost: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (feed_cost, user_id))
        conn.execute(
            "UPDATE animals SET hunger = ?, hunger_alerted = NULL WHERE animal_id = ?",
            (new_hunger, animal_id),
        )


# ── Breed ──────────────────────────────────────────────────────────────────────


def start_breed(
    user_id: int,
    animal_a_id: str,
    animal_b_id: str,
    offspring_species_id: int,
    ready_at: str,
    cost: int,
) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, user_id))
        conn.execute(
            "UPDATE animals SET is_breeding = 1 WHERE animal_id IN (?, ?)",
            (animal_a_id, animal_b_id),
        )
        conn.execute(
            "INSERT INTO breeding_queue "
            "(user_id, parent_a, parent_b, offspring_species_id, ready_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, animal_a_id, animal_b_id, offspring_species_id, ready_at),
        )


def collect_breed(
    user_id: int,
    animal_id: str,
    offspring_species_id: int,
    breed_id: int,
    parent_a: str,
    parent_b: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO animals (animal_id, user_id, species_id) VALUES (?, ?, ?)",
            (animal_id, user_id, offspring_species_id),
        )
        conn.execute(
            "UPDATE animals SET is_breeding = 0 WHERE animal_id IN (?, ?)",
            (parent_a, parent_b),
        )
        conn.execute("UPDATE breeding_queue SET collected = 1 WHERE id = ?", (breed_id,))


# ── Starter animal ────────────────────────────────────────────────────────────


def give_starter_animal(user_id: int):
    import random as _random
    import uuid as _uuid

    with get_conn() as conn:
        commons = conn.execute("SELECT * FROM species WHERE rarity = 'common'").fetchall()
        starter = _random.choice(commons)
        animal_id = str(_uuid.uuid4())
        conn.execute(
            "INSERT INTO animals (animal_id, user_id, species_id) VALUES (?, ?, ?)",
            (animal_id, user_id, starter["species_id"]),
        )
    return starter


# ── Species candidates ────────────────────────────────────────────────────────


def get_species_candidates(rarity: str, habitat: str | None = None) -> list:
    with get_conn() as conn:
        if habitat:
            return conn.execute(
                "SELECT * FROM species WHERE rarity = ? AND habitat = ?", (rarity, habitat)
            ).fetchall()
        return conn.execute("SELECT * FROM species WHERE rarity = ?", (rarity,)).fetchall()


# ── Zoo helpers ───────────────────────────────────────────────────────────────


def get_breeding_animal_ids(user_id: int) -> set:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT parent_a, parent_b FROM breeding_queue WHERE user_id = ? AND collected = 0",
            (user_id,),
        ).fetchall()
    result = set()
    for r in rows:
        result.add(r["parent_a"])
        result.add(r["parent_b"])
    return result


# ── Store atomic helpers ──────────────────────────────────────────────────────


def buy_item(user_id: int, item_key: str, price: int) -> None:
    """Atomically deduct coins and record the purchase."""
    with get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (price, user_id))
        conn.execute(
            "INSERT INTO user_purchases (user_id, item_key) VALUES (?, ?)", (user_id, item_key)
        )


# ── Scheduler helpers ─────────────────────────────────────────────────────────


def decay_animal_hunger(user_id: int, massaged: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE animals SET hunger = MAX(0, hunger - "
            "(SELECT CASE WHEN ? THEN hunger_decay / 2 ELSE hunger_decay END "
            "FROM species WHERE species_id = animals.species_id)) "
            "WHERE user_id = ? AND is_breeding = 0",
            (1 if massaged else 0, user_id),
        )


# ── Admin helpers ─────────────────────────────────────────────────────────────

_ANIMAL_STAT_SQL: dict[str, str] = {
    "hunger": "UPDATE animals SET hunger = ? WHERE animal_id = ?",
}


def adjust_coins(user_id: int, delta: int) -> None:
    """Add (or remove) coins, floored at 0."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = MAX(0, coins + ?) WHERE user_id = ?", (delta, user_id)
        )


def get_species_by_name(name: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM species WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()


def get_all_species_names() -> list:
    with get_conn() as conn:
        return [
            r["name"] for r in conn.execute("SELECT name FROM species ORDER BY name").fetchall()
        ]


def set_group_paused_until(group_chat_id: int, paused_until: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET paused_until = ? WHERE group_chat_id = ?",
            (paused_until, group_chat_id),
        )


def reset_user_data(user_id: int) -> None:
    with get_conn() as conn:
        animal_ids = [
            r["animal_id"]
            for r in conn.execute(
                "SELECT animal_id FROM animals WHERE user_id = ?", (user_id,)
            ).fetchall()
        ]
        if animal_ids:
            placeholders = ",".join("?" * len(animal_ids))
            conn.execute(
                f"DELETE FROM breeding_queue WHERE parent_a IN ({placeholders}) OR parent_b IN ({placeholders})",
                animal_ids + animal_ids,
            )
        conn.execute("DELETE FROM animals WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM mood_checkins WHERE user_id = ?", (user_id,))
        conn.execute(
            "UPDATE users SET coins = 100, streak_windows = 0, consecutive_misses = 0, "
            "last_prompt_at = NULL, last_checkin_at = NULL, paused_until = NULL WHERE user_id = ?",
            (user_id,),
        )


def get_bot_stats() -> dict:
    with get_conn() as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        animals = conn.execute("SELECT COUNT(*) FROM animals").fetchone()[0]
        breeding = conn.execute(
            "SELECT COUNT(*) FROM breeding_queue WHERE collected = 0"
        ).fetchone()[0]
        checkins = conn.execute("SELECT COUNT(*) FROM mood_checkins").fetchone()[0]
        by_rarity = conn.execute(
            "SELECT s.rarity, COUNT(*) as n FROM animals a "
            "JOIN species s ON s.species_id = a.species_id GROUP BY s.rarity"
        ).fetchall()
    return {
        "users": users,
        "animals": animals,
        "breeding": breeding,
        "checkins": checkins,
        "by_rarity": by_rarity,
    }


def admin_set_animal_stat(animal_id: str, stat: str, value: int) -> None:
    sql = _ANIMAL_STAT_SQL[stat]  # KeyError for unrecognised stats — caller validates
    with get_conn() as conn:
        conn.execute(sql, (value, animal_id))


# ── Trivia ────────────────────────────────────────────────────────────────────


def get_last_trivia_at(user_id: int) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT asked_at FROM trivia_log WHERE user_id = ? ORDER BY asked_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return row["asked_at"] if row else None


def record_trivia(user_id: int, now_str: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO trivia_log (user_id, asked_at) VALUES (?, ?)", (user_id, now_str))


# ── Daily ─────────────────────────────────────────────────────────────────────


def get_last_daily_at(user_id: int) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT claimed_at FROM daily_log WHERE user_id = ? ORDER BY claimed_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return row["claimed_at"] if row else None


def claim_daily(user_id: int, coins: int, new_streak: int, now_str: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO daily_log (user_id, claimed_at) VALUES (?, ?)", (user_id, now_str)
        )
        conn.execute(
            "UPDATE users SET coins = coins + ?, daily_streak = ? WHERE user_id = ?",
            (coins, new_streak, user_id),
        )


# ── Sell ──────────────────────────────────────────────────────────────────────


def sell_animal(user_id: int, animal_id: str, price: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM breeding_queue WHERE parent_a = ? OR parent_b = ?",
            (animal_id, animal_id),
        )
        conn.execute(
            "DELETE FROM trades WHERE proposer_animal_id = ? OR recipient_animal_id = ?",
            (animal_id, animal_id),
        )
        conn.execute("DELETE FROM animals WHERE animal_id = ?", (animal_id,))
        conn.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (price, user_id))


# ── Name ──────────────────────────────────────────────────────────────────────


def set_animal_nickname(animal_id: str, nickname: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE animals SET nickname = ? WHERE animal_id = ?", (nickname, animal_id))


# ── Scheduler streak / miss helpers ───────────────────────────────────────────


def reset_user_streak(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET consecutive_misses = 0, streak_windows = 0 WHERE user_id = ?",
            (user_id,),
        )


def set_consecutive_misses(user_id: int, misses: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET consecutive_misses = ? WHERE user_id = ?", (misses, user_id))


def bulk_set_last_prompt_at(member_ids: list, now_str: str) -> None:
    with get_conn() as conn:
        conn.executemany(
            "UPDATE users SET last_prompt_at = ? WHERE user_id = ?",
            [(now_str, uid) for uid in member_ids],
        )


def remove_starved_animal(animal_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM breeding_queue WHERE parent_a = ? OR parent_b = ?",
            (animal_id, animal_id),
        )
        conn.execute(
            "DELETE FROM trades WHERE proposer_animal_id = ? OR recipient_animal_id = ?",
            (animal_id, animal_id),
        )
        conn.execute("DELETE FROM animals WHERE animal_id = ?", (animal_id,))


def set_hunger_alerted(animal_id: str, threshold: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE animals SET hunger_alerted = ? WHERE animal_id = ?", (threshold, animal_id)
        )


# ── Achievement query helpers ─────────────────────────────────────────────────


def count_mood_checkins(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM mood_checkins WHERE user_id = ?", (user_id,)
        ).fetchone()[0]


def count_animals(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM animals WHERE user_id = ?", (user_id,)
        ).fetchone()[0]


def user_owns_rarity(user_id: int, rarity: str) -> bool:
    with get_conn() as conn:
        return (
            conn.execute(
                "SELECT COUNT(*) FROM animals a JOIN species s ON s.species_id = a.species_id "
                "WHERE a.user_id = ? AND s.rarity = ?",
                (user_id, rarity),
            ).fetchone()[0]
            > 0
        )


def count_collected_breeds(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM breeding_queue WHERE user_id = ? AND collected = 1",
            (user_id,),
        ).fetchone()[0]


def user_bred_rarity(user_id: int, rarity: str) -> bool:
    with get_conn() as conn:
        return (
            conn.execute(
                "SELECT COUNT(*) FROM breeding_queue bq "
                "JOIN species s ON s.species_id = bq.offspring_species_id "
                "WHERE bq.user_id = ? AND bq.collected = 1 AND s.rarity = ?",
                (user_id, rarity),
            ).fetchone()[0]
            > 0
        )


def count_distinct_species(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT species_id) FROM animals WHERE user_id = ?", (user_id,)
        ).fetchone()[0]


def count_distinct_species_in_habitat(user_id: int, habitat: str) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT a.species_id) FROM animals a "
            "JOIN species s ON s.species_id = a.species_id "
            "WHERE a.user_id = ? AND s.habitat = ?",
            (user_id, habitat),
        ).fetchone()[0]


def user_owns_all_rarities(user_id: int) -> bool:
    with get_conn() as conn:
        return (
            conn.execute(
                "SELECT COUNT(DISTINCT s.rarity) FROM animals a "
                "JOIN species s ON s.species_id = a.species_id WHERE a.user_id = ?",
                (user_id,),
            ).fetchone()[0]
            >= 4
        )


def user_has_max_enclosure(user_id: int, max_level: int) -> bool:
    with get_conn() as conn:
        return (
            conn.execute(
                "SELECT COUNT(*) FROM user_enclosures WHERE user_id = ? AND level = ?",
                (user_id, max_level),
            ).fetchone()[0]
            > 0
        )


def count_trivia_answered(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM trivia_log WHERE user_id = ?", (user_id,)
        ).fetchone()[0]


def get_active_group_chats() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT group_chat_id FROM users WHERE group_chat_id IS NOT NULL"
        ).fetchall()
        return [r["group_chat_id"] for r in rows]


# ── Bot settings ──────────────────────────────────────────────────────────────


def get_setting(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO bot_settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value),
        )


# ── Catch message persistence ─────────────────────────────────────────────────


def get_catch_message(user_id: int) -> tuple[int | None, int | None]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT catch_chat_id, catch_message_id FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return row["catch_chat_id"], row["catch_message_id"]
        return None, None


def set_catch_message(user_id: int, chat_id: int, message_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET catch_chat_id = ?, catch_message_id = ? WHERE user_id = ?",
            (chat_id, message_id, user_id),
        )
