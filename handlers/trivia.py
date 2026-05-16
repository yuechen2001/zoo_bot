import random
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db

TRIVIA_COOLDOWN_MINUTES = 15
TRIVIA_WINDOW_MINUTES = 10
COINS_CORRECT = 40
COINS_WRONG = 5


def _trivia_keyboard(tg_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("A", callback_data=f"trivia_{tg_id}_A"),
                InlineKeyboardButton("B", callback_data=f"trivia_{tg_id}_B"),
                InlineKeyboardButton("C", callback_data=f"trivia_{tg_id}_C"),
                InlineKeyboardButton("D", callback_data=f"trivia_{tg_id}_D"),
            ]
        ]
    )


async def trivia_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from game.trivia_data import QUESTIONS

    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    # Cooldown check
    with db.get_conn() as conn:
        last = conn.execute(
            "SELECT asked_at FROM trivia_log WHERE user_id = ? ORDER BY asked_at DESC LIMIT 1",
            (tg_id,),
        ).fetchone()

    if last:
        elapsed = (
            datetime.datetime.utcnow() - datetime.datetime.fromisoformat(last["asked_at"])
        ).total_seconds()
        remaining_s = TRIVIA_COOLDOWN_MINUTES * 60 - elapsed
        if remaining_s > 0:
            remaining_m = int(remaining_s // 60)
            await update.message.reply_text(
                f"⏳ Next trivia available in *{remaining_m} min*.",
                parse_mode="Markdown",
            )
            return

    q = random.choice(QUESTIONS)
    ctx.user_data["trivia"] = {
        "answer": q["answer"],
        "at": datetime.datetime.utcnow().isoformat(),
        "answered": False,
    }

    now_str = datetime.datetime.utcnow().isoformat()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO trivia_log (user_id, asked_at) VALUES (?, ?)",
            (tg_id, now_str),
        )

    opts = "\n".join(q["options"])
    await update.message.reply_text(
        f"🧠 *Animal Trivia!*\n\n{q['q']}\n\n{opts}",
        parse_mode="Markdown",
        reply_markup=_trivia_keyboard(tg_id),
    )


async def trivia_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_", 2)  # ["trivia", str(tg_id), option]
    target_id = int(parts[1])
    chosen = parts[2]

    if query.from_user.id != target_id:
        await query.answer("This isn't your question!", show_alert=True)
        return

    tg_id = query.from_user.id
    trivia = ctx.user_data.get("trivia")
    if not trivia:
        await query.answer("No active trivia — use /trivia to play!")
        return

    if trivia["answered"]:
        await query.answer("Already answered!")
        return

    # Check window
    elapsed = (
        datetime.datetime.utcnow() - datetime.datetime.fromisoformat(trivia["at"])
    ).total_seconds()
    if elapsed > TRIVIA_WINDOW_MINUTES * 60:
        ctx.user_data.pop("trivia", None)
        await query.answer("Too slow!")
        await query.edit_message_text("⏰ Time's up — the window closed. Try /trivia again later!")
        return

    trivia["answered"] = True
    correct = chosen == trivia["answer"]
    coins = COINS_CORRECT if correct else COINS_WRONG

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = coins + ? WHERE user_id = ?",
            (coins, tg_id),
        )

    if correct:
        await query.answer(f"✅ Correct! +{coins} coins")
        await query.edit_message_text(
            f"✅ *Correct!* The answer was *{trivia['answer']}*.\n💰 +{coins} coins!",
            parse_mode="Markdown",
        )
    else:
        await query.answer(f"❌ Wrong. +{coins} coins for trying")
        await query.edit_message_text(
            f"❌ *Wrong!* The correct answer was *{trivia['answer']}*.\n💰 +{coins} coins for trying.",
            parse_mode="Markdown",
        )
