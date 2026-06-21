import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.constants import MASSAGE_COST, MASSAGE_DURATION_HOURS, MASSAGE_COOLDOWN_HOURS
from utils import replace_command_ui


async def footmassage_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    def _fmt(seconds: float) -> str:
        total_m = int(seconds / 60)
        h, m = divmod(total_m, 60)
        return f"{h}h {m}m" if h else f"{m}m"

    # Check if massage is already active
    active_until = user["massage_active_until"]
    if active_until:
        until_dt = datetime.datetime.fromisoformat(active_until)
        if now < until_dt:
            remaining = until_dt - now
            msg = await update.message.reply_text(
                f"🦶 Your animals are still relaxed! {_fmt(remaining.total_seconds())} left on their massage."
            )
            await replace_command_ui(ctx, "footmassage_ui", update, msg)
            return

    # Check cooldown (massage_active_until is when it last expired)
    if active_until:
        last_end = datetime.datetime.fromisoformat(active_until)
        elapsed_hours = (now - last_end).total_seconds() / 3600
        if elapsed_hours < MASSAGE_COOLDOWN_HOURS:
            wait_secs = MASSAGE_COOLDOWN_HOURS * 3600 - (now - last_end).total_seconds()
            msg = await update.message.reply_text(
                f"⏳ Your animals need a break — massages are available every {MASSAGE_COOLDOWN_HOURS}h. "
                f"Try again in {_fmt(wait_secs)}."
            )
            await replace_command_ui(ctx, "footmassage_ui", update, msg)
            return

    if user["coins"] < MASSAGE_COST:
        msg = await update.message.reply_text(
            f"Not enough coins! A foot massage costs {MASSAGE_COST} 🪙 "
            f"(you have {user['coins']} 🪙)."
        )
        await replace_command_ui(ctx, "footmassage_ui", update, msg)
        return

    massage_until = (now + datetime.timedelta(hours=MASSAGE_DURATION_HOURS)).isoformat()
    db.activate_massage(tg_id, MASSAGE_COST, massage_until)

    msg = await update.message.reply_text(
        f"🦶 *Foot massage time!* (-{MASSAGE_COST} 🪙)\n\n"
        f"Your animals are blissfully relaxed for {MASSAGE_DURATION_HOURS}h — "
        f"hunger decay is halved until then. 😌",
        parse_mode="Markdown",
    )
    await replace_command_ui(ctx, "footmassage_ui", update, msg)
