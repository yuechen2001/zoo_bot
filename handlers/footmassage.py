import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db

MASSAGE_COST = 25
MASSAGE_DURATION_HOURS = 1
MASSAGE_COOLDOWN_HOURS = 4


async def footmassage_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    # Check if massage is already active
    active_until = user["massage_active_until"]
    if active_until:
        until_dt = datetime.datetime.fromisoformat(active_until)
        if now < until_dt:
            remaining = until_dt - now
            minutes = int(remaining.total_seconds() / 60)
            await update.message.reply_text(
                f"🦶 Your animals are still relaxed! {minutes}m left on their massage."
            )
            return

    # Check cooldown (massage_active_until is when it last expired)
    if active_until:
        last_end = datetime.datetime.fromisoformat(active_until)
        elapsed_hours = (now - last_end).total_seconds() / 3600
        if elapsed_hours < MASSAGE_COOLDOWN_HOURS:
            wait_minutes = int(
                (MASSAGE_COOLDOWN_HOURS * 3600 - (now - last_end).total_seconds()) / 60
            )
            await update.message.reply_text(
                f"⏳ Your animals need a break — massages are available every {MASSAGE_COOLDOWN_HOURS}h. "
                f"Try again in {wait_minutes}m."
            )
            return

    if user["coins"] < MASSAGE_COST:
        await update.message.reply_text(
            f"Not enough coins! A foot massage costs {MASSAGE_COST} 🪙 "
            f"(you have {user['coins']} 🪙)."
        )
        return

    massage_until = (now + datetime.timedelta(hours=MASSAGE_DURATION_HOURS)).isoformat()
    db.activate_massage(tg_id, MASSAGE_COST, massage_until)

    await update.message.reply_text(
        f"🦶 *Foot massage time!* (-{MASSAGE_COST} 🪙)\n\n"
        f"Your animals are blissfully relaxed for {MASSAGE_DURATION_HOURS}h — "
        f"hunger decay is halved until then. 😌",
        parse_mode="Markdown",
    )
