from telegram import Update
from telegram.ext import ContextTypes

import db
from game.quests_data import ARCS, CHAPTERS, check_quest_advance
from keyboards import quests_keyboard


async def quests_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    await check_quest_advance(tg_id, ctx)
    text = _render_quests(tg_id, arc=1)
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=quests_keyboard(tg_id, 1)
    )


async def quest_tab_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")  # quest_arc_{user_id}_{arc_num}
    user_id = int(parts[2])
    arc_num = int(parts[3])

    if query.from_user.id != user_id:
        await query.answer("Use /quests to see your own.", show_alert=True)
        return

    await query.answer()
    await check_quest_advance(user_id, ctx)
    text = _render_quests(user_id, arc=arc_num)
    try:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=quests_keyboard(user_id, arc_num),
        )
    except Exception:
        pass


def _render_quests(user_id: int, arc: int) -> str:
    progress_rows = db.get_quest_progress(user_id)
    progress = {r["chapter_num"]: r for r in progress_rows}
    active_ch = db.get_active_chapter(user_id) or 1

    arc_name = ARCS[arc]
    total_completed = sum(1 for r in progress_rows if r["completed_at"])
    lines = [
        f"📖 *Zoo Expedition* — {total_completed}/12 chapters complete",
        f"\n*Arc {arc}: {arc_name}*",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for ch_num, ch in CHAPTERS.items():
        if ch["arc"] != arc:
            continue

        row = progress.get(ch_num)
        completed = row and row["completed_at"]

        if completed:
            lines.append(f"✅ Ch {ch_num}: *{ch['title']}*")
        elif ch_num == active_ch:
            lines.append(f"▶️ Ch {ch_num}: *{ch['title']}*")
            lines.append(f"_{ch['intro']}_\n")

            user = db.get_user(user_id)
            for task in ch["tasks"]:
                done = task["check"](user_id, user)
                mark = "☑" if done else "☐"
                lines.append(f"  {mark} {task['desc']}")

            reward_parts = [f"+{ch['reward_coins']}🪙"]
            if ch["reward_species"]:
                sp = db.get_species_by_name(ch["reward_species"])
                if sp:
                    reward_parts.append(f"{sp['emoji']} {ch['reward_species']}")
            if ch["reward_title"]:
                reward_parts.append("🗺️ Expedition Leader title")
            lines.append(f"\n🏆 Reward: {' + '.join(reward_parts)}")
        else:
            lines.append(f"🔒 Ch {ch_num}: {ch['title']}")

    return "\n".join(lines)
