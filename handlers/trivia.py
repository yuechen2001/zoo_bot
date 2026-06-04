import random
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db
from game.achievements import triggers
from game.constants import (
    TRIVIA_COOLDOWN_MINUTES,
    TRIVIA_WINDOW_MINUTES,
    GROUP_TRIVIA_CORRECT_COINS,
    GROUP_TRIVIA_COUPLE_BONUS,
    GROUP_TRIVIA_WRONG_PENALTY,
)
from keyboards import trivia_wager_keyboard


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


def _group_trivia_keyboard(trivia_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("A", callback_data=f"gtrivia_{trivia_id}_A"),
                InlineKeyboardButton("B", callback_data=f"gtrivia_{trivia_id}_B"),
                InlineKeyboardButton("C", callback_data=f"gtrivia_{trivia_id}_C"),
                InlineKeyboardButton("D", callback_data=f"gtrivia_{trivia_id}_D"),
            ]
        ]
    )


async def trivia_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    last_at = db.get_last_trivia_at(tg_id)
    if last_at:
        elapsed = (
            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            - datetime.datetime.fromisoformat(last_at)
        ).total_seconds()
        remaining_s = TRIVIA_COOLDOWN_MINUTES * 60 - elapsed
        if remaining_s > 0:
            await update.message.reply_text(
                f"⏳ Next trivia available in *{int(remaining_s // 60)} min*.",
                parse_mode="Markdown",
            )
            return

    await update.message.reply_text(
        "🧠 *Animal Trivia — Place your wager!*\n\nHow many coins do you want to risk?",
        parse_mode="Markdown",
        reply_markup=trivia_wager_keyboard(tg_id, user["coins"]),
    )


async def trivia_wager_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from game.trivia_data import QUESTIONS

    query = update.callback_query
    parts = query.data.split("_", 3)  # ["trivia", "wager", str(tg_id), amount]
    target_id = int(parts[2])
    wager = int(parts[3])

    if query.from_user.id != target_id:
        await query.answer("This isn't your wager!", show_alert=True)
        return

    tg_id = query.from_user.id
    user = db.get_user(tg_id)
    if not user or user["coins"] < wager:
        await query.answer("Not enough coins!", show_alert=True)
        return

    q = random.choice(QUESTIONS)
    ctx.user_data["trivia"] = {
        "answer": q["answer"],
        "at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(),
        "answered": False,
        "wager": wager,
    }

    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    db.record_trivia(tg_id, now_str)

    opts = "\n".join(q["options"])
    await query.edit_message_text(
        f"🧠 *Animal Trivia!*  _(wager: {wager} 🪙)_\n\n{q['q']}\n\n{opts}",
        parse_mode="Markdown",
        reply_markup=_trivia_keyboard(tg_id),
    )


@triggers("trivia")
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

    elapsed = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.datetime.fromisoformat(trivia["at"])
    ).total_seconds()
    if elapsed > TRIVIA_WINDOW_MINUTES * 60:
        ctx.user_data.pop("trivia", None)
        await query.answer("Too slow!")
        await query.edit_message_text("⏰ Time's up — the window closed. Try /trivia again later!")
        return

    trivia["answered"] = True
    correct = chosen == trivia["answer"]
    wager = trivia.get("wager", 0)

    if correct:
        db.add_coins(tg_id, wager)
        await query.answer(f"✅ Correct! +{wager} coins")
        await query.edit_message_text(
            f"✅ *Correct!* The answer was *{trivia['answer']}*.\n💰 +{wager} coins!",
            parse_mode="Markdown",
        )
    else:
        db.add_coins(tg_id, -wager)
        await query.answer(f"❌ Wrong! -{wager} coins")
        await query.edit_message_text(
            f"❌ *Wrong!* The correct answer was *{trivia['answer']}*.\n💸 -{wager} coins.",
            parse_mode="Markdown",
        )


async def group_trivia_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_", 2)  # ["gtrivia", str(id), answer]
    trivia_id = int(parts[1])
    chosen = parts[2]

    tg_id = query.from_user.id
    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    trivia = db.get_group_trivia(trivia_id)
    if not trivia:
        await query.answer("No such trivia.", show_alert=True)
        return

    if trivia["resolved"]:
        await query.answer("This trivia is already over!", show_alert=True)
        return

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    expires = datetime.datetime.fromisoformat(trivia["expires_at"])
    if now > expires:
        await query.answer("Time's up — this trivia expired!", show_alert=True)
        return

    group_chat_id = trivia["group_chat_id"]
    correct = chosen == trivia["correct_answer"]

    if not correct:
        db.add_coins(tg_id, -GROUP_TRIVIA_WRONG_PENALTY)
        await query.answer(
            f"❌ Wrong! -{GROUP_TRIVIA_WRONG_PENALTY} 🪙. The answer was {trivia['correct_answer']}.",
            show_alert=True,
        )
        return

    first_uid = trivia["answered_by"]

    if first_uid is None:
        db.record_group_trivia_correct(trivia_id, tg_id)
        db.add_coins(tg_id, GROUP_TRIVIA_CORRECT_COINS)
        await query.answer(
            f"✅ Correct! +{GROUP_TRIVIA_CORRECT_COINS} 🪙. Waiting for your partner…",
            show_alert=True,
        )
        return

    if first_uid == tg_id:
        await query.answer("You already answered!", show_alert=True)
        return

    db.add_coins(tg_id, GROUP_TRIVIA_CORRECT_COINS)
    db.add_coins(tg_id, GROUP_TRIVIA_COUPLE_BONUS)
    db.add_coins(first_uid, GROUP_TRIVIA_COUPLE_BONUS)
    db.resolve_group_trivia(trivia_id)

    await query.answer(
        f"✅ Correct! Both answered — couple bonus! +{GROUP_TRIVIA_CORRECT_COINS + GROUP_TRIVIA_COUPLE_BONUS} 🪙",
        show_alert=True,
    )
    try:
        await ctx.bot.edit_message_text(
            chat_id=group_chat_id,
            message_id=trivia["message_id"],
            text=(
                f"🧠 *Group Trivia — Solved!*\n\n"
                f"The answer was *{trivia['correct_answer']}*.\n"
                f"Both players answered correctly — couple bonus! 🎉"
            ),
            parse_mode="Markdown",
        )
    except Exception:
        pass


def group_trivia_keyboard(trivia_id: int) -> InlineKeyboardMarkup:
    return _group_trivia_keyboard(trivia_id)
