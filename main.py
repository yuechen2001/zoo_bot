import logging
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from config import BOT_TOKEN, PROMPT_INTERVAL_MINUTES
from db import init_db
from scheduler import tick
from handlers import (
    admin_command,
    start_command,
    zoo_command,
    catch_command, catch_callback,
    feed_command,
    breed_command, breed_collect_callback,
    name_command,
    moodstart_command, moodstop_command,
    pause_command, resume_command,
    mood_checkin_callback,
    help_command,
)

logging.basicConfig(
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def handle_callback(update, ctx):
    data = update.callback_query.data
    if data.startswith("mood_"):
        await mood_checkin_callback(update, ctx)
    elif data.startswith("catch_"):
        await catch_callback(update, ctx)
    elif data == "breed_collect":
        await breed_collect_callback(update, ctx)
    else:
        await update.callback_query.answer("Unknown action")


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     start_command))
    app.add_handler(CommandHandler("zoo",       zoo_command))
    app.add_handler(CommandHandler("catch",     catch_command))
    app.add_handler(CommandHandler("feed",      feed_command))
    app.add_handler(CommandHandler("breed",     breed_command))
    app.add_handler(CommandHandler("name",      name_command))
    app.add_handler(CommandHandler("moodstart", moodstart_command))
    app.add_handler(CommandHandler("moodstop",  moodstop_command))
    app.add_handler(CommandHandler("pause",     pause_command))
    app.add_handler(CommandHandler("resume",    resume_command))
    app.add_handler(CommandHandler("help",      help_command))
    app.add_handler(CommandHandler("admin",     admin_command))
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.job_queue.run_repeating(
        tick,
        interval=PROMPT_INTERVAL_MINUTES * 60,
        first=30,
        job_kwargs={"misfire_grace_time": 60},
    )

    print(f"🦁 Zoo Bot is running! Mood prompts every {PROMPT_INTERVAL_MINUTES} min.")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
