import random
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.constants import SPIN_COST, WIN_3, WIN_2, SYMBOLS
from keyboards import slots_keyboard
from utils import replace_command_ui


async def slots_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    if user["coins"] < SPIN_COST:
        await update.message.reply_text(f"Not enough coins! A spin costs {SPIN_COST} 🪙.")
        return

    msg = await update.message.reply_text(
        f"🎰 *Slot Machine*\n\n"
        f"Each spin costs {SPIN_COST} 🪙.\n"
        f"3 of a kind: +{WIN_3} 🪙  |  2 of a kind: +{WIN_2} 🪙",
        parse_mode="Markdown",
        reply_markup=slots_keyboard(),
    )
    await replace_command_ui(ctx, "slots_ui", update, msg)


def _spin_result(reels: list) -> tuple[int, str]:
    counts = {s: reels.count(s) for s in set(reels)}
    max_match = max(counts.values())
    if max_match == 3:
        return WIN_3, f"🎉 *JACKPOT!* +{WIN_3} coins!"
    if max_match == 2:
        return WIN_2, f"✨ Two of a kind! +{WIN_2} coins!"
    return 0, "No match. Better luck next time!"


async def slots_spin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    if user["coins"] < SPIN_COST:
        await query.answer(f"Not enough coins! Need {SPIN_COST} 🪙.")
        return

    reels = [random.choice(SYMBOLS) for _ in range(3)]
    db.add_coins(tg_id, -SPIN_COST)
    winnings, result_line = _spin_result(reels)
    if winnings:
        db.add_coins(tg_id, winnings)

    user = db.get_user(tg_id)
    await query.answer()
    await query.edit_message_text(
        f"🎰  [ {reels[0]} | {reels[1]} | {reels[2]} ]\n\n"
        f"{result_line}\n"
        f"💰 {user['coins']} coins",
        parse_mode="Markdown",
        reply_markup=slots_keyboard(),
    )
