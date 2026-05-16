from telegram import Update
from telegram.ext import ContextTypes
import db


async def autofeed_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []

    if args and args[0].lower() == "off":
        db.set_autofeed(tg_id, None, None)
        await update.message.reply_text("⏹ Auto-feed disabled.")
        return

    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text(
            "Usage: /autofeed <threshold> <max\\_coins>\n"
            "Example: /autofeed 50 100 — feeds animals below 50 hunger, up to 100 🪙 per tick\n"
            "Turn off: /autofeed off",
            parse_mode="Markdown",
        )
        return

    threshold = int(args[0])
    max_coins = int(args[1])

    if not 1 <= threshold <= 100:
        await update.message.reply_text("Threshold must be between 1 and 100.")
        return
    if max_coins <= 0:
        await update.message.reply_text("Max coins must be greater than 0.")
        return

    db.set_autofeed(tg_id, threshold, max_coins)
    await update.message.reply_text(
        f"✅ Auto-feed on — will feed animals below *{threshold}* hunger, "
        f"up to *{max_coins}* 🪙 per tick.",
        parse_mode="Markdown",
    )
