import random
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.constants import SPIN_COST, WIN_3, WIN_2, SYMBOLS


async def slots_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    if user["coins"] < SPIN_COST:
        await update.message.reply_text(f"Not enough coins! A spin costs {SPIN_COST} 🪙.")
        return

    reels = [random.choice(SYMBOLS) for _ in range(3)]
    db.add_coins(tg_id, -SPIN_COST)

    counts = {s: reels.count(s) for s in set(reels)}
    max_match = max(counts.values())

    if max_match == 3:
        winnings = WIN_3
        result_line = f"🎉 *JACKPOT!* +{winnings} coins!"
    elif max_match == 2:
        winnings = WIN_2
        result_line = f"✨ Two of a kind! +{winnings} coins!"
    else:
        winnings = 0
        result_line = "No match. Better luck next time!"

    if winnings:
        db.add_coins(tg_id, winnings)

    user = db.get_user(tg_id)
    await update.message.reply_text(
        f"🎰  [ {reels[0]} | {reels[1]} | {reels[2]} ]\n\n"
        f"{result_line}\n"
        f"💰 {user['coins']} coins",
        parse_mode="Markdown",
    )
