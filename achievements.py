import db


def _animal_count(user_id):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM animals WHERE user_id = ?", (user_id,)
        ).fetchone()[0]


def _owns_rarity(user_id, rarity):
    with db.get_conn() as conn:
        return (
            conn.execute(
                "SELECT COUNT(*) FROM animals a JOIN species s ON s.species_id = a.species_id "
                "WHERE a.user_id = ? AND s.rarity = ?",
                (user_id, rarity),
            ).fetchone()[0]
            > 0
        )


def _breed_count(user_id):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM breeding_queue WHERE user_id = ? AND collected = 1",
            (user_id,),
        ).fetchone()[0]


def _bred_rarity(user_id, rarity):
    with db.get_conn() as conn:
        return (
            conn.execute(
                "SELECT COUNT(*) FROM breeding_queue bq "
                "JOIN species s ON s.species_id = bq.offspring_species_id "
                "WHERE bq.user_id = ? AND bq.collected = 1 AND s.rarity = ?",
                (user_id, rarity),
            ).fetchone()[0]
            > 0
        )


def _owns_all_rarities(user_id):
    with db.get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(DISTINCT s.rarity) FROM animals a "
            "JOIN species s ON s.species_id = a.species_id WHERE a.user_id = ?",
            (user_id,),
        ).fetchone()[0]
    return count >= 4


def _distinct_species_count(user_id):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT species_id) FROM animals WHERE user_id = ?", (user_id,)
        ).fetchone()[0]


def _checkin_count(user_id):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM mood_checkins WHERE user_id = ?", (user_id,)
        ).fetchone()[0]


# Each achievement: emoji, name, desc, trigger, check(user_id, user_row) -> bool
ACHIEVEMENTS = {
    # ── Mood / streak ─────────────────────────────────────────────────────────
    "first_checkin": {
        "emoji": "👣",
        "name": "First Step",
        "desc": "Complete your first mood check-in",
        "trigger": "checkin",
        "check": lambda uid, u: _checkin_count(uid) >= 1,
    },
    "streak_5": {
        "emoji": "🔥",
        "name": "On a Roll",
        "desc": "Reach a 5-window check-in streak",
        "trigger": "checkin",
        "check": lambda uid, u: (u["streak_windows"] or 0) >= 5,
    },
    "streak_10": {
        "emoji": "💫",
        "name": "Dedicated",
        "desc": "Reach a 10-window check-in streak",
        "trigger": "checkin",
        "check": lambda uid, u: (u["streak_windows"] or 0) >= 10,
    },
    "streak_25": {
        "emoji": "⚡",
        "name": "Unstoppable",
        "desc": "Reach a 25-window check-in streak",
        "trigger": "checkin",
        "check": lambda uid, u: (u["streak_windows"] or 0) >= 25,
    },
    "streak_50": {
        "emoji": "👑",
        "name": "Legendary Checker",
        "desc": "Reach a 50-window check-in streak",
        "trigger": "checkin",
        "check": lambda uid, u: (u["streak_windows"] or 0) >= 50,
    },
    # ── Catching ──────────────────────────────────────────────────────────────
    "first_catch": {
        "emoji": "🎯",
        "name": "First Catch",
        "desc": "Catch your first animal",
        "trigger": "catch",
        "check": lambda uid, u: _animal_count(uid) >= 1,
    },
    "zoo_5": {
        "emoji": "🦁",
        "name": "Zoo Opening",
        "desc": "Own 5 animals",
        "trigger": "catch",
        "check": lambda uid, u: _animal_count(uid) >= 5,
    },
    "zoo_10": {
        "emoji": "🌟",
        "name": "Zoo Master",
        "desc": "Own 10 animals",
        "trigger": "catch",
        "check": lambda uid, u: _animal_count(uid) >= 10,
    },
    "first_rare": {
        "emoji": "🟦",
        "name": "Rare Find",
        "desc": "Catch your first rare animal",
        "trigger": "catch",
        "check": lambda uid, u: _owns_rarity(uid, "rare"),
    },
    "first_epic": {
        "emoji": "🟪",
        "name": "Epic Discovery",
        "desc": "Catch your first epic animal",
        "trigger": "catch",
        "check": lambda uid, u: _owns_rarity(uid, "epic"),
    },
    "first_legendary": {
        "emoji": "🟨",
        "name": "Legend Hunter",
        "desc": "Catch your first legendary animal",
        "trigger": "catch",
        "check": lambda uid, u: _owns_rarity(uid, "legendary"),
    },
    # ── Breeding ──────────────────────────────────────────────────────────────
    "first_breed": {
        "emoji": "🥚",
        "name": "Parent",
        "desc": "Collect your first offspring",
        "trigger": "breed",
        "check": lambda uid, u: _breed_count(uid) >= 1,
    },
    "breed_5": {
        "emoji": "🐣",
        "name": "Breeder",
        "desc": "Collect 5 offspring",
        "trigger": "breed",
        "check": lambda uid, u: _breed_count(uid) >= 5,
    },
    "legendary_breed": {
        "emoji": "✨",
        "name": "Legendary Lineage",
        "desc": "Breed a legendary offspring",
        "trigger": "breed",
        "check": lambda uid, u: _bred_rarity(uid, "legendary"),
    },
    "epic_breed": {
        "emoji": "💜",
        "name": "Epic Lineage",
        "desc": "Breed an epic offspring",
        "trigger": "breed",
        "check": lambda uid, u: _bred_rarity(uid, "epic"),
    },
    "breed_10": {
        "emoji": "🐥",
        "name": "Prolific",
        "desc": "Collect 10 offspring",
        "trigger": "breed",
        "check": lambda uid, u: _breed_count(uid) >= 10,
    },
    # ── Zoo size & variety ────────────────────────────────────────────────────
    "zoo_20": {
        "emoji": "🐘",
        "name": "Full House",
        "desc": "Own 20 animals",
        "trigger": "catch",
        "check": lambda uid, u: _animal_count(uid) >= 20,
    },
    "all_rarities": {
        "emoji": "🌈",
        "name": "Collector",
        "desc": "Own at least one animal of every rarity",
        "trigger": "catch",
        "check": lambda uid, u: _owns_all_rarities(uid),
    },
    "species_10": {
        "emoji": "📚",
        "name": "Variety Pack",
        "desc": "Own 10 different species",
        "trigger": "catch",
        "check": lambda uid, u: _distinct_species_count(uid) >= 10,
    },
    # ── Mood milestones ───────────────────────────────────────────────────────
    "checkin_50": {
        "emoji": "🎭",
        "name": "Mood Master",
        "desc": "Complete 50 mood check-ins",
        "trigger": "checkin",
        "check": lambda uid, u: _checkin_count(uid) >= 50,
    },
    "coins_500": {
        "emoji": "💰",
        "name": "Coin Hoarder",
        "desc": "Accumulate 500 coins",
        "trigger": "checkin",
        "check": lambda uid, u: (u["coins"] or 0) >= 500,
    },
    # ── Trading ───────────────────────────────────────────────────────────────
    "first_trade": {
        "emoji": "🤝",
        "name": "Trader",
        "desc": "Complete your first animal trade",
        "trigger": "trade",
        "check": lambda uid, u: True,
    },
    # ── Selling ───────────────────────────────────────────────────────────────
    "first_sell": {
        "emoji": "💸",
        "name": "Merchant",
        "desc": "Sell your first animal",
        "trigger": "sell",
        "check": lambda uid, u: True,
    },
    # ── Feeding ───────────────────────────────────────────────────────────────
    "first_feed": {
        "emoji": "🍽",
        "name": "Caretaker",
        "desc": "Feed an animal for the first time",
        "trigger": "feed",
        "check": lambda uid, u: True,
    },
}


async def check_achievements(user_id: int, trigger: str, ctx):
    user = db.get_user(user_id)
    if not user:
        return

    earned = db.get_achievement_keys(user_id)
    newly_earned = []

    for key, ach in ACHIEVEMENTS.items():
        if key in earned or ach["trigger"] != trigger:
            continue
        if ach["check"](user_id, user):
            db.award_achievement(user_id, key)
            newly_earned.append(ach)

    if not newly_earned:
        return

    name = user.get("username") or "Someone"
    for ach in newly_earned:
        if user.get("group_chat_id"):
            try:
                await ctx.bot.send_message(
                    user["group_chat_id"],
                    f"🏆 *{name}* unlocked *{ach['name']}* {ach['emoji']}\n_{ach['desc']}_",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
