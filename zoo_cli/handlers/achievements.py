from telegram import Update
from telegram.ext import ContextTypes
import db
from game.achievements import ACHIEVEMENTS
from utils import replace_command_ui


def render_achievements(earned_keys: set, filter_type: str = "all") -> str:
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

    if filter_type == "earned":
        if earned_lines:
            parts.append("\n".join(earned_lines))
        else:
            parts.append("_None yet — get out there!_")
    elif filter_type == "locked":
        if locked_lines:
            parts.append("\n".join(locked_lines))
        else:
            parts.append("_You've unlocked everything!_ 🎉")
    else:
        if earned_lines:
            parts.append("\n".join(earned_lines))
        else:
            parts.append("_None yet — get out there!_")
        if locked_lines:
            parts.append("\n" + "\n".join(locked_lines))

    return "\n".join(parts)


async def achievements_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    from keyboards import achievements_keyboard

    earned_keys = db.get_achievement_keys(tg_id)
    text = render_achievements(earned_keys, "all")
    msg = await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=achievements_keyboard(tg_id, "all")
    )
    await replace_command_ui(ctx, "achievements_ui", update, msg)


async def achievements_tab_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 3)  # ach_tab_{user_id}_{filter}
    user_id = int(parts[2])
    filter_type = parts[3]

    if query.from_user.id != user_id:
        await query.answer("Use /achievements to see your own.", show_alert=True)
        return

    from keyboards import achievements_keyboard

    earned_keys = db.get_achievement_keys(user_id)
    text = render_achievements(earned_keys, filter_type)
    try:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=achievements_keyboard(user_id, filter_type),
        )
    except Exception:
        pass
