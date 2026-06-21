import random
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.constants import MAX_BET
from keyboards import gamble_keyboard
from utils import replace_command_ui


async def gamble_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if args and args[0].isdigit():
        amount = int(args[0])
        if amount < 1:
            await update.message.reply_text("Minimum bet is 1 🪙.")
            return
        if amount > MAX_BET:
            await update.message.reply_text(f"Max bet is {MAX_BET} 🪙.")
            return
        if user["coins"] < amount:
            await update.message.reply_text(f"Not enough coins! You have {user['coins']} 🪙.")
            return
        win = random.random() < 0.5
        db.add_coins(tg_id, amount if win else -amount)
        user = db.get_user(tg_id)
        if win:
            result = f"🪙 *Coin flip — Heads!*\n\n+{amount} coins! You now have {user['coins']} 🪙."
        else:
            result = f"🪙 *Coin flip — Tails!*\n\n-{amount} coins. You now have {user['coins']} 🪙."
        await update.message.reply_text(result, parse_mode="Markdown")
        return

    msg = await update.message.reply_text(
        f"🪙 *Coin Flip*\n\nPick your bet — 50% chance to double it.\nMax bet: {MAX_BET} 🪙",
        parse_mode="Markdown",
        reply_markup=gamble_keyboard(user["coins"]),
    )
    await replace_command_ui(ctx, "gamble_ui", update, msg)


async def gamble_bet_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    amount = int(query.data.removeprefix("gamble_bet_"))

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    if amount > MAX_BET:
        await query.answer(f"Max bet is {MAX_BET} 🪙.")
        return

    if user["coins"] < amount:
        await query.answer(f"Not enough coins! You have {user['coins']} 🪙.")
        return

    win = random.random() < 0.5
    db.add_coins(tg_id, amount if win else -amount)
    user = db.get_user(tg_id)

    if win:
        result = f"🪙 *Coin flip — Heads!*\n\n+{amount} coins! You now have {user['coins']} 🪙."
    else:
        result = f"🪙 *Coin flip — Tails!*\n\n-{amount} coins. You now have {user['coins']} 🪙."

    await query.answer()
    await query.edit_message_text(
        result,
        parse_mode="Markdown",
        reply_markup=gamble_keyboard(user["coins"]),
    )
