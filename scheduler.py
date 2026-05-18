import datetime
import logging
import telegram
import db
import random
from config import (
    CHECKIN_WINDOW_MINUTES,
    PROMPT_INTERVAL_MINUTES,
    BREED_READY_REMINDER_MINUTES,
    WILD_EVENT_MIN_MINUTES,
    WILD_EVENT_MAX_MINUTES,
    WILD_EVENT_EXPIRY_MINUTES,
)
from keyboards import mood_keyboard, breed_collect_keyboard
from game.species_data import ENCLOSURE_LEVELS, HABITATS, RARITY_LABELS
from game.constants import WILD_EVENT_RARITY_WEIGHTS
from utils import format_mention

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()


async def prompt_tick(ctx):
    """Runs every PROMPT_INTERVAL_MINUTES. Sends mood prompts."""
    t0 = datetime.datetime.now(datetime.timezone.utc)
    logger.info("prompt_tick: start")
    db.set_setting("last_prompt_tick_at", _now_iso())
    await _send_mood_prompts(ctx)
    logger.info(
        "prompt_tick: done in %.2fs",
        (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(),
    )


async def hunger_tick(ctx):
    """Runs every HUNGER_INTERVAL_MINUTES. Decays animal hunger."""
    t0 = datetime.datetime.now(datetime.timezone.utc)
    logger.info("hunger_tick: start")
    db.set_setting("last_hunger_tick_at", _now_iso())
    await _decay_stats()
    logger.info(
        "hunger_tick: done in %.2fs",
        (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(),
    )


async def job_tick(ctx):
    """Runs every JOB_INTERVAL_MINUTES. Checks starvation, breeding, alerts, autofeed."""
    t0 = datetime.datetime.now(datetime.timezone.utc)
    logger.info("job_tick: start")
    db.set_setting("last_job_tick_at", _now_iso())
    await _check_starved_animals(ctx)
    await _check_breed_completions(ctx)
    await _check_hunger_alerts(ctx)
    await _autofeed(ctx)
    logger.info(
        "job_tick: done in %.2fs",
        (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(),
    )


async def cleanup(ctx):
    """Runs every minute. Expires stale trades and closes expired prompt windows."""
    t0 = datetime.datetime.now(datetime.timezone.utc)
    logger.info("cleanup: start")
    await _cleanup_expired_trades(ctx)
    await _cleanup_expired_prompts(ctx)
    logger.info(
        "cleanup: done in %.2fs",
        (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(),
    )


async def enclosure_income(ctx):
    """Runs every hour. Credits pending enclosure coins and notifies."""
    t0 = datetime.datetime.now(datetime.timezone.utc)
    logger.info("enclosure_income: start")
    db.set_setting("last_enclosure_tick_at", _now_iso())
    await _tick_enclosure_income(ctx)
    logger.info(
        "enclosure_income: done in %.2fs",
        (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(),
    )


async def _send_mood_prompts(ctx):
    users = db.get_all_active_users()
    if not users:
        return

    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()

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
                    db.reset_user_streak(tg_id)
                    reset_names.append(user["username"] or f"user {tg_id}")
                else:
                    db.set_consecutive_misses(tg_id, new_misses)

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

        # Don't send a new prompt if one was sent recently — checked against DB so restarts are safe
        group_state = db.get_group_state(group_chat_id)
        if group_state and group_state["last_prompt_at"]:
            elapsed_s = (
                datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                - datetime.datetime.fromisoformat(group_state["last_prompt_at"])
            ).total_seconds()
            if elapsed_s < PROMPT_INTERVAL_MINUTES * 60:
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
            db.set_group_last_prompt(group_chat_id, now_str)
            db.bulk_set_last_prompt_at([u["user_id"] for u in members], now_str)
        except Exception:
            logger.exception("Failed to send mood prompt to %s", group_chat_id)


async def _decay_stats():
    users = db.get_all_users_with_animals()
    for user in users:
        uid = user["user_id"]
        massaged = (
            user["massage_active_until"] is not None
            and user["massage_active_until"]
            > datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
        )
        db.decay_animal_hunger(uid, massaged)


async def _check_starved_animals(ctx):
    starved = db.get_starved_animals()
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
        db.remove_starved_animal(animal["animal_id"])


async def _check_breed_completions(ctx):
    ready = db.get_ready_breeds(BREED_READY_REMINDER_MINUTES)
    for breed in ready:
        group_chat_id = breed["group_chat_id"]
        if not group_chat_id:
            continue
        is_reminder = breed["last_notified_at"] is not None
        prefix = "🔔 *Breed ready reminder!*" if is_reminder else "🥚 *Breeding complete!*"
        mention = format_mention(breed["username"], breed["user_id"])
        try:
            await ctx.bot.send_message(
                group_chat_id,
                f"{prefix} ({mention})\n"
                f"{breed['emoji_a']} {breed['name_a']} × {breed['emoji_b']} {breed['name_b']} "
                f"→ {breed['emoji_offspring']} {breed['name_offspring']}\n\n"
                f"Use `/breed collect` to claim your new animal!",
                parse_mode="Markdown",
                reply_markup=breed_collect_keyboard(),
            )
            db.mark_breed_notified(breed["id"])
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
        db.set_hunger_alerted(animal["animal_id"], threshold)


async def _tick_enclosure_income(ctx):
    from collections import defaultdict

    group_earnings: dict = defaultdict(list)

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
            db.add_pending_enclosure_coins(uid, total_coins)
            pending_total = db.get_pending_enclosure_coins(uid)
            mention = format_mention(user["username"], uid)
            if user["group_chat_id"]:
                group_earnings[user["group_chat_id"]].append((mention, total_coins, pending_total))

    for group_chat_id, earnings in group_earnings.items():
        lines = ["🏦 *Enclosure income ready!*"]
        for mention, coins, pending_total in earnings:
            lines.append(f"  {mention}: +{coins} 🪙 (total pending: {pending_total} 🪙)")
        lines.append("\nUse `/enclosures collect` to claim.")
        try:
            await ctx.bot.send_message(group_chat_id, "\n".join(lines), parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to send enclosure income to %s", group_chat_id)


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
    from game.constants import FEED_COST_BY_RARITY, FEED_HUNGER

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
        fed_lines = []
        for animal in animals:
            cost = FEED_COST_BY_RARITY.get(animal["rarity"], 10)
            if spent + cost > budget:
                break
            new_hunger = min(100, animal["hunger"] + FEED_HUNGER)
            db.feed_animal(uid, animal["animal_id"], new_hunger, cost)
            name = animal["nickname"] or animal["species_name"]
            fed_lines.append(
                f"{animal['emoji']} {name}: {animal['hunger']}→{new_hunger} (-{cost} 🪙)"
            )
            spent += cost

        try:
            if not fed_lines:
                await ctx.bot.send_message(
                    chat_id,
                    "⚠️ Auto-feed skipped — not enough coins.",
                )
            else:
                remaining = current_user["coins"] - spent
                lines = "\n".join(fed_lines)
                await ctx.bot.send_message(
                    chat_id,
                    f"🍖 *Auto-feed* ({format_mention(user['username'], uid)})\n{lines}\n\nBalance: {remaining} 🪙",
                    parse_mode="Markdown",
                )
        except Exception:
            logger.exception("Failed to send autofeed message to %s", chat_id)


async def _cleanup_expired_prompts(ctx):
    prompt_messages = ctx.bot_data.get("prompt_messages", {})
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
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
            except telegram.error.BadRequest:
                pass  # already removed or message deleted — nothing to do
            except Exception:
                logger.exception("Failed to remove prompt markup in %s", group_chat_id)
            to_remove.append(group_chat_id)
    for g in to_remove:
        del prompt_messages[g]


async def wild_event_tick(ctx):
    """Post a wild animal sighting to each active group, then reschedule itself at a random interval."""
    t0 = datetime.datetime.now(datetime.timezone.utc)
    logger.info("wild_event_tick: start")
    from handlers.wild_event import wild_catch_keyboard

    groups = db.get_active_group_chats()
    for group_chat_id in groups:
        rarity = random.choices(
            ["common", "rare", "epic", "legendary"],
            weights=WILD_EVENT_RARITY_WEIGHTS,
        )[0]
        candidates = db.get_species_candidates(rarity)
        species = random.choice(candidates) if candidates else None
        if not species:
            continue
        try:
            msg = await ctx.bot.send_message(
                group_chat_id,
                f"🌿 *A wild {species['emoji']} {species['name']} appeared!*\n"
                f"{RARITY_LABELS[species['rarity']]} | {HABITATS[species['habitat']]['emoji']} {HABITATS[species['habitat']]['name']}\n\n"
                f"Catch rate: {int(species['catch_rate'] * 100)}%\n\n"
                f"You have 5 min to decide.",
                parse_mode="Markdown",
                reply_markup=wild_catch_keyboard(0),
            )
            event_id = db.create_wild_event(group_chat_id, species["species_id"], msg.message_id)
            await ctx.bot.edit_message_reply_markup(
                chat_id=group_chat_id,
                message_id=msg.message_id,
                reply_markup=wild_catch_keyboard(event_id),
            )
        except Exception:
            logger.exception("Failed to send wild event to %s", group_chat_id)

    delay = random.randint(WILD_EVENT_MIN_MINUTES, WILD_EVENT_MAX_MINUTES) * 60
    next_at = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(seconds=delay)
    ).isoformat()
    db.set_setting("next_wild_event_at", next_at)
    logger.info(
        "wild_event_tick: done in %.2fs, next in %ds",
        (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(),
        delay,
    )
    ctx.job_queue.run_once(wild_event_tick, delay, name="wild_event_tick")


async def cleanup_expired_wild_events(ctx):
    """Expire unclaimed wild events and edit their messages to show they're gone."""
    t0 = datetime.datetime.now(datetime.timezone.utc)
    logger.info("cleanup_expired_wild_events: start")
    expired = db.get_expired_wild_events(WILD_EVENT_EXPIRY_MINUTES)
    for event in expired:
        try:
            await ctx.bot.edit_message_text(
                chat_id=event["group_chat_id"],
                message_id=event["message_id"],
                text="🌿 *The wild animal got away!* Better luck next time.",
                parse_mode="Markdown",
            )
        except Exception:
            pass
        db.claim_wild_event(event["id"], -1)
    logger.info(
        "cleanup_expired_wild_events: done in %.2fs",
        (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(),
    )
