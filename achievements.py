import db
from species_data import MAX_ENCLOSURE_LEVEL


# Each achievement: emoji, name, desc, trigger, check(user_id, user_row) -> bool
ACHIEVEMENTS = {
    # ── Mood / streak ─────────────────────────────────────────────────────────
    "first_checkin": {
        "emoji": "👣",
        "name": "First Step",
        "desc": "Complete your first mood check-in",
        "trigger": "checkin",
        "check": lambda uid, u: db.count_mood_checkins(uid) >= 1,
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
        "check": lambda uid, u: db.count_animals(uid) >= 1,
    },
    "zoo_5": {
        "emoji": "🦁",
        "name": "Zoo Opening",
        "desc": "Own 5 animals",
        "trigger": "catch",
        "check": lambda uid, u: db.count_animals(uid) >= 5,
    },
    "zoo_10": {
        "emoji": "🌟",
        "name": "Zoo Master",
        "desc": "Own 10 animals",
        "trigger": "catch",
        "check": lambda uid, u: db.count_animals(uid) >= 10,
    },
    "first_rare": {
        "emoji": "🟦",
        "name": "Rare Find",
        "desc": "Catch your first rare animal",
        "trigger": "catch",
        "check": lambda uid, u: db.user_owns_rarity(uid, "rare"),
    },
    "first_epic": {
        "emoji": "🟪",
        "name": "Epic Discovery",
        "desc": "Catch your first epic animal",
        "trigger": "catch",
        "check": lambda uid, u: db.user_owns_rarity(uid, "epic"),
    },
    "first_legendary": {
        "emoji": "🟨",
        "name": "Legend Hunter",
        "desc": "Catch your first legendary animal",
        "trigger": "catch",
        "check": lambda uid, u: db.user_owns_rarity(uid, "legendary"),
    },
    # ── Breeding ──────────────────────────────────────────────────────────────
    "first_breed": {
        "emoji": "🥚",
        "name": "Parent",
        "desc": "Collect your first offspring",
        "trigger": "breed",
        "check": lambda uid, u: db.count_collected_breeds(uid) >= 1,
    },
    "breed_5": {
        "emoji": "🐣",
        "name": "Breeder",
        "desc": "Collect 5 offspring",
        "trigger": "breed",
        "check": lambda uid, u: db.count_collected_breeds(uid) >= 5,
    },
    "legendary_breed": {
        "emoji": "✨",
        "name": "Legendary Lineage",
        "desc": "Breed a legendary offspring",
        "trigger": "breed",
        "check": lambda uid, u: db.user_bred_rarity(uid, "legendary"),
    },
    "epic_breed": {
        "emoji": "💜",
        "name": "Epic Lineage",
        "desc": "Breed an epic offspring",
        "trigger": "breed",
        "check": lambda uid, u: db.user_bred_rarity(uid, "epic"),
    },
    "breed_10": {
        "emoji": "🐥",
        "name": "Prolific",
        "desc": "Collect 10 offspring",
        "trigger": "breed",
        "check": lambda uid, u: db.count_collected_breeds(uid) >= 10,
    },
    # ── Zoo size & variety ────────────────────────────────────────────────────
    "zoo_20": {
        "emoji": "🐘",
        "name": "Full House",
        "desc": "Own 20 animals",
        "trigger": "catch",
        "check": lambda uid, u: db.count_animals(uid) >= 20,
    },
    "all_rarities": {
        "emoji": "🌈",
        "name": "Collector",
        "desc": "Own at least one animal of every rarity",
        "trigger": "catch",
        "check": lambda uid, u: db.user_owns_all_rarities(uid),
    },
    "species_10": {
        "emoji": "📚",
        "name": "Variety Pack",
        "desc": "Own 10 different species",
        "trigger": "catch",
        "check": lambda uid, u: db.count_distinct_species(uid) >= 10,
    },
    # ── Mood milestones ───────────────────────────────────────────────────────
    "checkin_50": {
        "emoji": "🎭",
        "name": "Mood Master",
        "desc": "Complete 50 mood check-ins",
        "trigger": "checkin",
        "check": lambda uid, u: db.count_mood_checkins(uid) >= 50,
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
    # ── Trivia ────────────────────────────────────────────────────────────────
    "first_trivia": {
        "emoji": "🧠",
        "name": "Curious Mind",
        "desc": "Answer your first trivia question",
        "trigger": "trivia",
        "check": lambda uid, u: True,
    },
    "trivia_10": {
        "emoji": "📚",
        "name": "Quiz Whiz",
        "desc": "Answer 10 trivia questions",
        "trigger": "trivia",
        "check": lambda uid, u: db.count_trivia_answered(uid) >= 10,
    },
    # ── Daily ─────────────────────────────────────────────────────────────────
    "first_daily": {
        "emoji": "🌅",
        "name": "Early Bird",
        "desc": "Claim your first daily reward",
        "trigger": "daily",
        "check": lambda uid, u: True,
    },
    # ── Wild events ───────────────────────────────────────────────────────────
    "first_wild": {
        "emoji": "⚡",
        "name": "Quick Reflexes",
        "desc": "Catch your first wild event animal",
        "trigger": "wild_catch",
        "check": lambda uid, u: True,
    },
    # ── Store ─────────────────────────────────────────────────────────────────
    "first_purchase": {
        "emoji": "🛍",
        "name": "Shopkeeper",
        "desc": "Buy your first item from the store",
        "trigger": "store",
        "check": lambda uid, u: True,
    },
    # ── Gifts ─────────────────────────────────────────────────────────────────
    "first_gift": {
        "emoji": "🎁",
        "name": "Generous Soul",
        "desc": "Give an animal to another player",
        "trigger": "gift",
        "check": lambda uid, u: True,
    },
    # ── Enclosures ────────────────────────────────────────────────────────────
    "first_upgrade": {
        "emoji": "🏗",
        "name": "Builder",
        "desc": "Upgrade an enclosure for the first time",
        "trigger": "enclosure",
        "check": lambda uid, u: True,
    },
    "max_enclosure": {
        "emoji": "🏛",
        "name": "Master Architect",
        "desc": "Reach max level on any enclosure",
        "trigger": "enclosure",
        "check": lambda uid, u: db.user_has_max_enclosure(uid, MAX_ENCLOSURE_LEVEL),
    },
    # ── Coins ─────────────────────────────────────────────────────────────────
    "coins_1000": {
        "emoji": "💎",
        "name": "Wealthy",
        "desc": "Accumulate 1,000 coins",
        "trigger": "checkin",
        "check": lambda uid, u: (u["coins"] or 0) >= 1000,
    },
    "coins_5000": {
        "emoji": "🏦",
        "name": "Tycoon",
        "desc": "Accumulate 5,000 coins",
        "trigger": "checkin",
        "check": lambda uid, u: (u["coins"] or 0) >= 5000,
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

    name = user["username"] or "Someone"
    for ach in newly_earned:
        if user["group_chat_id"]:
            try:
                await ctx.bot.send_message(
                    user["group_chat_id"],
                    f"🏆 *{name}* unlocked *{ach['name']}* {ach['emoji']}\n_{ach['desc']}_",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
