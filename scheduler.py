import datetime
import logging
import db
from config import CHECKIN_WINDOW_MINUTES
from keyboards import mood_keyboard
from species_data import ENCLOSURE_LEVELS

logger = logging.getLogger(__name__)


async def prompt_tick(ctx):
    """Runs every PROMPT_INTERVAL_MINUTES. Sends mood prompts."""
    await _send_mood_prompts(ctx)


async def job_tick(ctx):
    """Runs every JOB_INTERVAL_MINUTES. Decays stats, checks breeding, autofeeds."""
    await _decay_stats()
    await _check_starved_animals(ctx)
    await _check_breed_completions(ctx)
    await _check_hunger_alerts(ctx)
    await _autofeed(ctx)


async def cleanup(ctx):
    """Runs every minute. Expires stale trades and closes expired prompt windows."""
    await _cleanup_expired_trades(ctx)
    await _cleanup_expired_prompts(ctx)


async def enclosure_income(ctx):
    """Runs every hour. Awards passive coin income from enclosures."""
    await _tick_enclosure_income()


async def _send_mood_prompts(ctx):
    users = db.get_all_active_users()
    if not users:
        return

    now_str = datetime.datetime.utcnow().isoformat()

    from collections import defaultdict

    by_group = defaultdict(list)
    for u in users:
        by_group[u["group_chat_id"]].append(u)

    for group_chat_id, members in by_group.items():
        reset_names = []
        for user in members:
            tg_id = user["user_id"]
            last_prompt = user["last_prompt_at"]
            responded = last_prompt and db.has_prompt_response(group_chat_id, last_prompt, tg_id)
            if last_prompt and not responded:
                new_misses = (user["consecutive_misses"] or 0) + 1
                if new_misses >= 2:
                    with db.get_conn() as conn:
                        conn.execute(
                            "UPDATE users SET consecutive_misses = 0, streak_windows = 0 WHERE user_id = ?",
                            (tg_id,),
                        )
                    reset_names.append(user["username"] or f"user {tg_id}")
                else:
                    with db.get_conn() as conn:
                        conn.execute(
                            "UPDATE users SET consecutive_misses = ? WHERE user_id = ?",
                            (new_misses, tg_id),
                        )

        if reset_names:
            if len(reset_names) == 1:
                msg = f"💔 *{reset_names[0]}* missed 2 check-ins in a row — streak reset to 0!"
            else:
                names = " & ".join(f"*{n}*" for n in reset_names)
                msg = f"💔 {names} both missed 2 check-ins in a row — streaks reset to 0!"
            try:
                await ctx.bot.send_message(group_chat_id, msg, parse_mode="Markdown")
            except Exception:
                logger.exception("Failed to send streak-reset message to %s", group_chat_id)

        # Don't send a new prompt if the last one is still within the checkin window
        last_sent = ctx.bot_data.get("prompt_messages", {}).get(group_chat_id)
        if last_sent:
            elapsed = (
                datetime.datetime.utcnow() - datetime.datetime.fromisoformat(last_sent["sent_at"])
            ).total_seconds() / 60
            if elapsed < CHECKIN_WINDOW_MINUTES:
                continue

        try:
            msg = await ctx.bot.send_message(
                group_chat_id,
                "🕐 *Mood check-in!* How are you feeling right now?",
                parse_mode="Markdown",
                reply_markup=mood_keyboard(),
            )
            ctx.bot_data.setdefault("prompt_messages", {})[group_chat_id] = {
                "message_id": msg.message_id,
                "sent_at": now_str,
            }
            with db.get_conn() as conn:
                conn.executemany(
                    "UPDATE users SET last_prompt_at = ? WHERE user_id = ?",
                    [(now_str, u["user_id"]) for u in members],
                )
        except Exception:
            logger.exception("Failed to send mood prompt to %s", group_chat_id)


async def _decay_stats():
    users = db.get_all_users_with_animals()
    for user in users:
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE animals SET "
                "hunger = MAX(0, hunger - (SELECT hunger_decay FROM species WHERE species_id = animals.species_id)) "
                "WHERE user_id = ? AND is_breeding = 0",
                (user["user_id"],),
            )


async def _check_starved_animals(ctx):
    with db.get_conn() as conn:
        starved = conn.execute(
            "SELECT a.animal_id, a.user_id, a.nickname, s.name, s.emoji, u.group_chat_id "
            "FROM animals a "
            "JOIN species s ON s.species_id = a.species_id "
            "JOIN users u ON u.user_id = a.user_id "
            "WHERE a.hunger = 0 AND a.is_breeding = 0"
        ).fetchall()

    for animal in starved:
        name = animal["nickname"] or animal["name"]
        chat_id = animal["group_chat_id"] or animal["user_id"]
        try:
            await ctx.bot.send_message(
                chat_id,
                f"💔 *{animal['emoji']} {name}* ran away — they were too hungry!",
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Failed to send starved-animal message to %s", chat_id)
        with db.get_conn() as conn:
            conn.execute("DELETE FROM animals WHERE animal_id = ?", (animal["animal_id"],))


async def _check_breed_completions(ctx):
    ready = db.get_ready_breeds()
    for breed in ready:
        group_chat_id = breed["group_chat_id"]
        if not group_chat_id:
            continue
        try:
            await ctx.bot.send_message(
                group_chat_id,
                f"🥚 *Breeding complete!*\n"
                f"{breed['emoji_a']} {breed['name_a']} × {breed['emoji_b']} {breed['name_b']} "
                f"→ {breed['emoji_offspring']} {breed['name_offspring']}\n\n"
                f"Use `/breed collect` to claim your new animal!",
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Failed to send breed-complete message to %s", group_chat_id)


async def _check_hunger_alerts(ctx):
    animals = db.get_low_hunger_animals()
    for animal in animals:
        hunger = animal["hunger"]
        alerted = animal["hunger_alerted"]
        chat_id = animal["group_chat_id"] or animal["user_id"]
        name = animal["nickname"] or animal["name"]

        if hunger <= 10 and alerted != 10:
            msg = f"🚨 *{animal['emoji']} {name}* is starving! (hunger: {hunger})\nFeed them now with /feed!"
            threshold = 10
        elif hunger <= 20 and alerted is None:
            msg = f"⚠️ *{animal['emoji']} {name}* is getting hungry. (hunger: {hunger})\nUse /feed to top them up!"
            threshold = 20
        else:
            continue

        try:
            await ctx.bot.send_message(chat_id, msg, parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to send hunger alert to %s", chat_id)
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE animals SET hunger_alerted = ? WHERE animal_id = ?",
                (threshold, animal["animal_id"]),
            )


async def _tick_enclosure_income():
    for user in db.get_all_users_with_animals():
        uid = user["user_id"]
        enclosures = db.get_enclosures(uid)
        total_coins = 0
        for habitat, level in enclosures.items():
            rate = ENCLOSURE_LEVELS[level]["coins_per_animal_hr"]
            if rate == 0:
                continue
            count = db.get_animal_count_by_habitat(uid, habitat)
            total_coins += rate * count
        if total_coins > 0:
            db.add_coins(uid, total_coins)


async def _cleanup_expired_trades(ctx):
    expired = db.expire_old_trades()
    for trade in expired:
        proposer = db.get_user(trade["proposer_id"])
        if not proposer:
            continue
        chat_id = proposer["group_chat_id"] or proposer["user_id"]
        try:
            await ctx.bot.send_message(
                chat_id,
                "⏰ Your trade offer expired — no response in time.",
            )
        except Exception:
            logger.exception("Failed to send trade-expiry message to %s", chat_id)


async def _autofeed(ctx):
    from handlers.feed import FEED_COST_BY_RARITY, FEED_HUNGER

    for user in db.get_autofeed_users():
        uid = user["user_id"]
        threshold = user["autofeed_threshold"]
        max_coins = user["autofeed_max_coins"]
        chat_id = user["group_chat_id"] or uid

        animals = db.get_animals_below_hunger(uid, threshold)
        if not animals:
            continue

        current_user = db.get_user(uid)
        budget = min(max_coins, current_user["coins"])

        spent = 0
        fed_count = 0
        for animal in animals:
            cost = FEED_COST_BY_RARITY.get(animal["rarity"], 10)
            if spent + cost > budget:
                break
            new_hunger = min(100, animal["hunger"] + FEED_HUNGER)
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE users SET coins = coins - ? WHERE user_id = ?",
                    (cost, uid),
                )
                conn.execute(
                    "UPDATE animals SET hunger = ?, hunger_alerted = NULL WHERE animal_id = ?",
                    (new_hunger, animal["animal_id"]),
                )
            spent += cost
            fed_count += 1

        try:
            if fed_count == 0:
                await ctx.bot.send_message(
                    chat_id,
                    "⚠️ Auto-feed skipped — not enough coins.",
                )
            else:
                remaining = current_user["coins"] - spent
                plural = "s" if fed_count != 1 else ""
                await ctx.bot.send_message(
                    chat_id,
                    f"🍖 Auto-fed {fed_count} animal{plural} — spent {spent} 🪙 (balance: {remaining} 🪙)",
                )
        except Exception:
            logger.exception("Failed to send autofeed message to %s", chat_id)


async def _cleanup_expired_prompts(ctx):
    prompt_messages = ctx.bot_data.get("prompt_messages", {})
    now = datetime.datetime.utcnow()
    to_remove = []
    for group_chat_id, info in list(prompt_messages.items()):
        sent_at = datetime.datetime.fromisoformat(info["sent_at"])
        if (now - sent_at).total_seconds() / 60 > CHECKIN_WINDOW_MINUTES:
            try:
                await ctx.bot.edit_message_reply_markup(
                    chat_id=group_chat_id,
                    message_id=info["message_id"],
                    reply_markup=None,
                )
            except Exception:
                logger.exception("Failed to remove prompt markup in %s", group_chat_id)
            to_remove.append(group_chat_id)
    for g in to_remove:
        del prompt_messages[g]
