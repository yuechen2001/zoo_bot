from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db
from game.achievements import check_achievements
from keyboards import animal_picker_keyboard


async def sell_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if args and args[0].isdigit():
        await _sell_direct(update, tg_id, int(args[0]), ctx)
        return

    animals = db.get_animals(tg_id)
    if not animals:
        await update.message.reply_text("You have no animals to sell.")
        return

    kb = animal_picker_keyboard(animals, "sell_pick", "sell_cancel")
    await update.message.reply_text("Which animal do you want to sell?", reply_markup=kb)


async def _sell_direct(update, tg_id, position, ctx):
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
    db.sell_animal(tg_id, animal["animal_id"], sell_price)
    await check_achievements(tg_id, "sell", ctx)

    await update.message.reply_text(
        f"💸 Sold {animal['emoji']} *{name}* for *{sell_price}* 🪙\n"
        f"_(hunger {animal['hunger']}/100 × base {base} 🪙)_",
        parse_mode="Markdown",
    )


async def sell_pick_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    pos = int(query.data.removeprefix("sell_pick_"))

    animal = db.get_animal_by_position(tg_id, pos)
    if not animal:
        await query.answer("That animal no longer exists.", show_alert=True)
        return

    name = animal["nickname"] or animal["species_name"]

    if animal["is_breeding"]:
        await query.answer(f"{name} is currently breeding — can't sell!", show_alert=True)
        return

    if db.has_pending_trade_for_animal(animal["animal_id"]):
        await query.answer(f"{name} has a pending trade — can't sell!", show_alert=True)
        return

    base = animal["catch_cost"] // 2
    sell_price = max(1, round(base * animal["hunger"] / 100))

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"✅ Sell for {sell_price} 🪙", callback_data=f"sell_yes_{pos}"
                ),
                InlineKeyboardButton("❌ Cancel", callback_data="sell_cancel"),
            ]
        ]
    )
    await query.answer()
    await query.edit_message_text(
        f"{animal['emoji']} *{name}* — sell for *{sell_price}* 🪙?\n"
        f"_(hunger {animal['hunger']}/100 × base {base} 🪙)_",
        reply_markup=kb,
        parse_mode="Markdown",
    )


async def sell_yes_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    pos = int(query.data.removeprefix("sell_yes_"))

    animal = db.get_animal_by_position(tg_id, pos)
    if not animal:
        await query.answer("That animal no longer exists.", show_alert=True)
        await query.edit_message_text("Sell cancelled — animal not found.")
        return

    name = animal["nickname"] or animal["species_name"]

    if animal["is_breeding"]:
        await query.answer(f"{name} is now breeding — can't sell!", show_alert=True)
        return

    if db.has_pending_trade_for_animal(animal["animal_id"]):
        await query.answer(f"{name} has a pending trade — can't sell!", show_alert=True)
        return

    base = animal["catch_cost"] // 2
    sell_price = max(1, round(base * animal["hunger"] / 100))
    db.sell_animal(tg_id, animal["animal_id"], sell_price)
    await check_achievements(tg_id, "sell", ctx)

    await query.answer()
    await query.edit_message_text(
        f"💸 Sold {animal['emoji']} *{name}* for *{sell_price}* 🪙",
        parse_mode="Markdown",
    )


async def sell_cancel_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Cancelled")
    await query.edit_message_text("Sell cancelled.")
