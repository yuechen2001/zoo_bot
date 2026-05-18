import random
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.constants import MAX_BET


async def gamble_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text(
            f"Usage: /gamble <amount>\nExample: /gamble 50\nMax bet: {MAX_BET} 🪙"
        )
        return

    amount = int(ctx.args[0])

    if amount <= 0:
        await update.message.reply_text("Bet must be at least 1 coin.")
        return

    if amount > MAX_BET:
        await update.message.reply_text(f"Max bet is {MAX_BET} 🪙.")
        return

    if user["coins"] < amount:
        await update.message.reply_text(f"Not enough coins! You have {user['coins']} 🪙.")
        return

    win = random.random() < 0.5
    delta = amount if win else -amount

    db.add_coins(tg_id, delta)

    new_coins = user["coins"] + delta
    if win:
        await update.message.reply_text(
            f"🪙 *Coin flip — Heads!*\n\n+{amount} coins! You now have {new_coins} 🪙.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"🪙 *Coin flip — Tails!*\n\n-{amount} coins. You now have {new_coins} 🪙.",
            parse_mode="Markdown",
        )
