from telegram import Update
from telegram.ext import ContextTypes
import db
from achievements import check_achievements


async def sell_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /sell <position>\nExample: /sell 2")
        return

    position = int(args[0])
    animal = db.get_animal_by_position(tg_id, position)
    if not animal:
        await update.message.reply_text(f"No animal at position #{position}.")
        return

    name = animal["nickname"] or animal["species_name"]

    if animal["is_breeding"]:
        await update.message.reply_text(
            f"{animal['emoji']} *{name}* is currently breeding — can't sell!",
            parse_mode="Markdown",
        )
        return

    if db.has_pending_trade_for_animal(animal["animal_id"]):
        await update.message.reply_text(
            f"{animal['emoji']} *{name}* has a pending trade — can't sell!",
            parse_mode="Markdown",
        )
        return

    base = animal["catch_cost"] // 2
    sell_price = max(1, round(base * animal["hunger"] / 100))

    db.delete_animal(animal["animal_id"])
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (sell_price, tg_id))

    await update.message.reply_text(
        f"💸 Sold {animal['emoji']} *{name}* for *{sell_price}* 🪙\n"
        f"_(hunger {animal['hunger']}/100 × base {base} 🪙)_",
        parse_mode="Markdown",
    )
    await check_achievements(tg_id, "sell", ctx)
