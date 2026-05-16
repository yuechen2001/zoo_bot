import logging
from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from config import BOT_TOKEN, PROMPT_INTERVAL_MINUTES
from db import init_db
from scheduler import tick, cleanup, enclosure_income
from handlers import (
    achievements_command,
    admin_command,
    start_command,
    zoo_command,
    catch_command,
    catch_callback,
    feed_command,
    breed_command,
    breed_collect_callback,
    name_command,
    moodstart_command,
    moodstop_command,
    pause_command,
    resume_command,
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
)

logging.basicConfig(
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def post_init(application):
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Join and get your starter animal"),
            BotCommand("zoo", "See your zoo"),
            BotCommand("catch", "Search for a wild animal"),
            BotCommand("feed", "Feed animals (10 🪙 each)"),
            BotCommand("breed", "Breed two animals"),
            BotCommand("name", "Give an animal a nickname"),
            BotCommand("moodstart", "Opt in to mood prompts"),
            BotCommand("moodstop", "Opt out of prompts"),
            BotCommand("resume", "End pause early"),
            BotCommand("achievements", "View achievements"),
            BotCommand("trivia", "Answer animal trivia for coins"),
            BotCommand("gamble", "Bet coins on a coin flip"),
            BotCommand("daily", "Claim your daily coin reward"),
            BotCommand("slots", "Spin the slot machine (10 coins)"),
            BotCommand("trade", "Offer an animal trade to another player"),
            BotCommand("invest", "Invest coins for a 25% return after 24h"),
            BotCommand("sell", "Sell an animal for coins"),
            BotCommand("enclosures", "View and upgrade your enclosures"),
            BotCommand("directory", "Browse all animals & see which you own"),
            BotCommand("help", "Show all commands"),
        ]
    )


async def handle_callback(update, ctx):
    data = update.callback_query.data
    if data.startswith("mood_"):
        await mood_checkin_callback(update, ctx)
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
    else:
        await update.callback_query.answer("Unknown action")


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
    app.add_handler(CommandHandler("pause", pause_command))
    app.add_handler(CommandHandler("resume", resume_command))
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
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.job_queue.run_repeating(
        tick,
        interval=PROMPT_INTERVAL_MINUTES * 60,
        first=30,
        job_kwargs={"misfire_grace_time": 60},
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
        first=3600,
        job_kwargs={"misfire_grace_time": 300},
    )

    print(f"🦁 Zoo Bot is running! Mood prompts every {PROMPT_INTERVAL_MINUTES} min.")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
