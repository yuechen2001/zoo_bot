import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db

DAILY_COINS = 50
DAILY_COOLDOWN_HOURS = 24


async def daily_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    with db.get_conn() as conn:
        last = conn.execute(
            "SELECT claimed_at FROM daily_log WHERE user_id = ? ORDER BY claimed_at DESC LIMIT 1",
            (tg_id,),
        ).fetchone()

    if last:
        elapsed = (
            datetime.datetime.utcnow() - datetime.datetime.fromisoformat(last["claimed_at"])
        ).total_seconds()
        remaining_s = DAILY_COOLDOWN_HOURS * 3600 - elapsed
        if remaining_s > 0:
            remaining_h = int(remaining_s // 3600)
            remaining_m = int((remaining_s % 3600) // 60)
            await update.message.reply_text(
                f"⏳ Daily reward available in *{remaining_h}h {remaining_m}m*.",
                parse_mode="Markdown",
            )
            return

    now_str = datetime.datetime.utcnow().isoformat()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO daily_log (user_id, claimed_at) VALUES (?, ?)",
            (tg_id, now_str),
        )
        conn.execute(
            "UPDATE users SET coins = coins + ? WHERE user_id = ?",
            (DAILY_COINS, tg_id),
        )

    user = db.get_user(tg_id)
    await update.message.reply_text(
        f"🎁 *Daily reward!*\n\n+{DAILY_COINS} coins!\nYou now have {user['coins']} 🪙.\n\nCome back tomorrow for more!",
        parse_mode="Markdown",
    )
