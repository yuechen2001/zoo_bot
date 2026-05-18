import logging
from logging.handlers import RotatingFileHandler
from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

import datetime
import random as _random

from config import (
    BOT_TOKEN,
    HUNGER_INTERVAL_MINUTES,
    JOB_INTERVAL_MINUTES,
    PROMPT_INTERVAL_MINUTES,
    WILD_EVENT_MIN_MINUTES,
    WILD_EVENT_MAX_MINUTES,
)
import db as db_module
from db import init_db
from scheduler import (
    prompt_tick,
    hunger_tick,
    job_tick,
    cleanup,
    enclosure_income,
    wild_event_tick,
    cleanup_expired_wild_events,
)
from handlers import (
    achievements_command,
    admin_command,
    start_command,
    autofeed_command,
    zoo_command,
    zoo_page_callback,
    catch_command,
    catch_callback,
    catch_lure_callback,
    feed_command,
    breed_command,
    breed_collect_callback,
    name_command,
    moodstart_command,
    moodstop_command,
    mood_checkin_callback,
    help_command,
    trivia_command,
    trivia_callback,
    gamble_command,
    daily_command,
    slots_command,
    trade_command,
    trade_callback,
    invest_command,
    sell_command,
    enclosures_command,
    enclosure_upgrade_callback,
    directory_command,
    inventory_command,
    inventory_callback,
)
from handlers.gift import gift_command
from handlers.store import store_command, store_callback
from handlers.footmassage import footmassage_command
from handlers.wild_event import wild_event_callback

_log_fmt = logging.Formatter("%(asctime)s  %(name)s  %(levelname)s  %(message)s")
_file_handler = RotatingFileHandler("zoo_bot.log", maxBytes=5 * 1024 * 1024, backupCount=3)
_file_handler.setFormatter(_log_fmt)

logging.basicConfig(
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(), _file_handler],
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def post_init(application):
    await application.bot.set_my_commands(
        [
            BotCommand("admin", "Admin & mod tools — /admin help for full list"),
            BotCommand("start", "Join and get your starter animal"),
            BotCommand("zoo", "See your zoo"),
            BotCommand("footmassage", "Halve hunger decay for 1h (25 🪙, 4h cooldown)"),
            BotCommand("catch", "Search for a wild animal"),
            BotCommand("feed", "Feed animals (10 🪙 each)"),
            BotCommand("breed", "Breed two animals"),
            BotCommand("name", "Give an animal a nickname"),
            BotCommand("moodstart", "Opt in to mood prompts"),
            BotCommand("moodstop", "Opt out of prompts"),
            BotCommand("achievements", "View achievements"),
            BotCommand("trivia", "Answer animal trivia for coins"),
            BotCommand("gamble", "Bet coins on a coin flip"),
            BotCommand("daily", "Claim your daily coin reward"),
            BotCommand("slots", "Spin the slot machine (10 coins)"),
            BotCommand("trade", "Offer an animal trade to another player"),
            BotCommand("invest", "Invest coins for a 25% return after 24h"),
            BotCommand("sell", "Sell an animal for coins"),
            BotCommand("enclosures", "View, upgrade enclosures, and collect income"),
            BotCommand("directory", "Browse all animals & see which you own"),
            BotCommand("autofeed", "Auto-feed animals below a hunger threshold each tick"),
            BotCommand("gift", "Give an animal to another player"),
            BotCommand("store", "Browse the item store"),
            BotCommand("inventory", "Your bag — use items and equip titles"),
            BotCommand("help", "Show all commands"),
        ]
    )


async def error_handler(_update, ctx):
    logger.exception("Unhandled exception in handler", exc_info=ctx.error)


async def handle_callback(update, ctx):
    data = update.callback_query.data
    if data.startswith("mood_"):
        await mood_checkin_callback(update, ctx)
    elif data.startswith("catch_lure_"):
        await catch_lure_callback(update, ctx)
    elif data.startswith("catch_"):
        await catch_callback(update, ctx)
    elif data == "breed_collect":
        await breed_collect_callback(update, ctx)
    elif data.startswith("trivia_"):
        await trivia_callback(update, ctx)
    elif data.startswith("trade_"):
        await trade_callback(update, ctx)
    elif data.startswith("enc_upgrade_"):
        await enclosure_upgrade_callback(update, ctx)
    elif data.startswith("zoo_page_"):
        await zoo_page_callback(update, ctx)
    elif data.startswith("wild_catch_"):
        await wild_event_callback(update, ctx)
    elif data.startswith("store_buy_"):
        await store_callback(update, ctx)
    elif data.startswith("inv_use_") or data.startswith("inv_equip_"):
        await inventory_callback(update, ctx)
    elif data == "zoo_noop":
        await update.callback_query.answer()
    else:
        await update.callback_query.answer("Unknown action")


def _first_delay(setting_key: str, interval_s: int, default_s: int) -> float:
    """Compute initial job delay from DB so events resume on their natural cadence after restart."""
    raw = db_module.get_setting(setting_key)
    if not raw:
        return default_s
    last = datetime.datetime.fromisoformat(raw)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    elapsed = (now - last).total_seconds()
    return max(10.0, interval_s - elapsed)


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("zoo", zoo_command))
    app.add_handler(CommandHandler("catch", catch_command))
    app.add_handler(CommandHandler("feed", feed_command))
    app.add_handler(CommandHandler("breed", breed_command))
    app.add_handler(CommandHandler("name", name_command))
    app.add_handler(CommandHandler("moodstart", moodstart_command))
    app.add_handler(CommandHandler("moodstop", moodstop_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("achievements", achievements_command))
    app.add_handler(CommandHandler("trivia", trivia_command))
    app.add_handler(CommandHandler("gamble", gamble_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("slots", slots_command))
    app.add_handler(CommandHandler("trade", trade_command))
    app.add_handler(CommandHandler("invest", invest_command))
    app.add_handler(CommandHandler("sell", sell_command))
    app.add_handler(CommandHandler("enclosures", enclosures_command))
    app.add_handler(CommandHandler("directory", directory_command))
    app.add_handler(CommandHandler("autofeed", autofeed_command))
    app.add_handler(CommandHandler("gift", gift_command))
    app.add_handler(CommandHandler("store", store_command))
    app.add_handler(CommandHandler("inventory", inventory_command))
    app.add_handler(CommandHandler("footmassage", footmassage_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    prompt_interval = PROMPT_INTERVAL_MINUTES * 60
    hunger_interval = HUNGER_INTERVAL_MINUTES * 60
    job_interval = JOB_INTERVAL_MINUTES * 60

    app.job_queue.run_repeating(
        prompt_tick,
        interval=prompt_interval,
        first=_first_delay("last_prompt_tick_at", prompt_interval, 30),
        job_kwargs={"misfire_grace_time": 60},
    )
    app.job_queue.run_repeating(
        hunger_tick,
        interval=hunger_interval,
        first=_first_delay("last_hunger_tick_at", hunger_interval, hunger_interval),
        job_kwargs={"misfire_grace_time": 60},
    )
    app.job_queue.run_repeating(
        job_tick,
        interval=job_interval,
        first=_first_delay("last_job_tick_at", job_interval, 10),
        job_kwargs={"misfire_grace_time": 30},
    )
    app.job_queue.run_repeating(
        cleanup,
        interval=60,
        first=10,
        job_kwargs={"misfire_grace_time": 30},
    )
    app.job_queue.run_repeating(
        enclosure_income,
        interval=3600,
        first=_first_delay("last_enclosure_tick_at", 3600, 3600),
        job_kwargs={"misfire_grace_time": 300},
    )
    app.job_queue.run_repeating(
        cleanup_expired_wild_events,
        interval=600,
        first=60,
        job_kwargs={"misfire_grace_time": 60},
    )

    # Wild event: resume from DB-stored next-fire time, else random fresh delay
    next_wild_raw = db_module.get_setting("next_wild_event_at")
    if next_wild_raw:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        next_wild = datetime.datetime.fromisoformat(next_wild_raw)
        wild_delay = max(10.0, (next_wild - now).total_seconds())
    else:
        wild_delay = _random.randint(WILD_EVENT_MIN_MINUTES, WILD_EVENT_MAX_MINUTES) * 60

    app.job_queue.run_once(
        wild_event_tick,
        wild_delay,
        name="wild_event_tick",
    )

    logger.info(
        "Zoo Bot is running! Prompts every %d min, hunger every %d min, "
        "job tick every %d min, enclosure income every 60 min, "
        "wild events every %d–%d min.",
        PROMPT_INTERVAL_MINUTES,
        HUNGER_INTERVAL_MINUTES,
        JOB_INTERVAL_MINUTES,
        WILD_EVENT_MIN_MINUTES,
        WILD_EVENT_MAX_MINUTES,
    )
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
