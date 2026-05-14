from telegram import Update
from telegram.ext import ContextTypes
import db
from achievements import ACHIEVEMENTS


async def achievements_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    earned_keys = db.get_achievement_keys(tg_id)
    total = len(ACHIEVEMENTS)
    count = len(earned_keys)

    earned_lines = []
    locked_lines = []

    for key, ach in ACHIEVEMENTS.items():
        if key in earned_keys:
            earned_lines.append(f"{ach['emoji']} *{ach['name']}* — {ach['desc']}")
        else:
            locked_lines.append(f"🔒 {ach['name']} — {ach['desc']}")

    parts = [f"🏆 *Achievements* ({count}/{total})\n"]

    if earned_lines:
        parts.append("\n".join(earned_lines))
    else:
        parts.append("_None yet — get out there!_")

    if locked_lines:
        parts.append("\n" + "\n".join(locked_lines))

    await update.message.reply_text("\n".join(parts), parse_mode="Markdown")
