import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.achievements import check_achievements
from game.constants import DAILY_COOLDOWN_HOURS, DAILY_STREAK_EXPIRY_HOURS, DAILY_TIERS


def _daily_coins(streak: int) -> int:
    for threshold, coins in DAILY_TIERS:
        if streak >= threshold:
            return coins
    return 50


def _next_tier(streak: int) -> tuple[int, int] | None:
    """Return (days_needed, coins) for the next tier, or None if already at max."""
    for threshold, coins in DAILY_TIERS:
        if streak < threshold:
            return threshold, coins
    return None


async def daily_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    last_at = db.get_last_daily_at(tg_id)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    if last_at:
        elapsed_s = (now - datetime.datetime.fromisoformat(last_at)).total_seconds()
        remaining_s = DAILY_COOLDOWN_HOURS * 3600 - elapsed_s
        if remaining_s > 0:
            remaining_h = int(remaining_s // 3600)
            remaining_m = int((remaining_s % 3600) // 60)
            await update.message.reply_text(
                f"⏳ Daily reward available in *{remaining_h}h {remaining_m}m*.",
                parse_mode="Markdown",
            )
            return

        # Determine new streak
        if elapsed_s <= DAILY_STREAK_EXPIRY_HOURS * 3600:
            new_streak = (user["daily_streak"] or 0) + 1
        else:
            new_streak = 1  # missed a day — reset
    else:
        new_streak = 1

    coins = _daily_coins(new_streak)
    db.claim_daily(tg_id, coins, new_streak, now.isoformat())

    user = db.get_user(tg_id)
    next_tier = _next_tier(new_streak)

    next_line = (
        f"\n_Next tier: Day {next_tier[0]} → {next_tier[1]} 🪙_"
        if next_tier
        else "\n_You're at the max tier! 🏆_"
    )

    await update.message.reply_text(
        f"🎁 *Daily reward — Day {new_streak}!*\n\n"
        f"+{coins} 🪙 (you have {user['coins']} 🪙)"
        f"{next_line}",
        parse_mode="Markdown",
    )
    await check_achievements(tg_id, "daily", ctx)
