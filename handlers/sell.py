from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db
from game.achievements import check_achievements
from keyboards import animal_picker_keyboard


def _sell_price(animal) -> tuple[int, int]:
    base = animal["catch_cost"] // 2
    return base, max(1, round(base * animal["hunger"] / 100))


def _sell_confirm_keyboard(animal) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"✅ Sell for {_sell_price(animal)[1]} 🪙",
                    callback_data=f"sell_yes_{animal['animal_id']}",
                ),
                InlineKeyboardButton("❌ Cancel", callback_data="sell_cancel"),
            ]
        ]
    )


def _sell_confirm_text(animal) -> str:
    name = animal["nickname"] or animal["species_name"]
    base, sell_price = _sell_price(animal)
    return (
        f"{animal['emoji']} *{name}* — sell for *{sell_price}* 🪙?\n"
        f"_(hunger {animal['hunger']}/100 × base {base} 🪙)_"
    )


async def _clear_sell_message(ctx: ContextTypes.DEFAULT_TYPE, tg_id: int) -> None:
    prev = ctx.user_data.get("sell_msg")
    if prev:
        try:
            await ctx.bot.delete_message(chat_id=prev["chat_id"], message_id=prev["msg_id"])
        except Exception:
            pass
        ctx.user_data.pop("sell_msg", None)


async def sell_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    await _clear_sell_message(ctx, tg_id)

    animals = db.get_animals(tg_id)
    if not animals:
        await update.message.reply_text("You have no animals to sell.")
        return

    # /sell <number> — jump straight to confirm screen
    if ctx.args and ctx.args[0].isdigit():
        pos = int(ctx.args[0])
        animal = db.get_animal_by_position(tg_id, pos)
        if not animal:
            await update.message.reply_text(
                f"No animal at position {pos}. You have {len(animals)} animal(s)."
            )
            return
        name = animal["nickname"] or animal["species_name"]
        if animal["is_breeding"]:
            await update.message.reply_text(f"{name} is currently breeding — can't sell!")
            return
        if db.has_pending_trade_for_animal(animal["animal_id"]):
            await update.message.reply_text(f"{name} has a pending trade — can't sell!")
            return
        msg = await update.message.reply_text(
            _sell_confirm_text(animal),
            reply_markup=_sell_confirm_keyboard(animal),
            parse_mode="Markdown",
        )
        ctx.user_data["sell_msg"] = {"chat_id": msg.chat_id, "msg_id": msg.message_id}
        return

    kb = animal_picker_keyboard(
        animals, "sell_pick", "sell_cancel", page=0, page_callback_prefix="sell_page"
    )
    msg = await update.message.reply_text("Which animal do you want to sell?", reply_markup=kb)
    ctx.user_data["sell_msg"] = {"chat_id": msg.chat_id, "msg_id": msg.message_id}


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

    await query.answer()
    await query.edit_message_text(
        _sell_confirm_text(animal),
        reply_markup=_sell_confirm_keyboard(animal),
        parse_mode="Markdown",
    )


async def sell_yes_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    animal_id = query.data.removeprefix("sell_yes_")

    animal = db.get_animal(animal_id)
    if not animal or animal["user_id"] != tg_id:
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

    base, sell_price = _sell_price(animal)
    db.sell_animal(tg_id, animal["animal_id"], sell_price)
    await check_achievements(tg_id, "sell", ctx)

    await query.answer()
    remaining = db.get_animals(tg_id)
    if remaining:
        kb = animal_picker_keyboard(
            remaining, "sell_pick", "sell_cancel", page=0, page_callback_prefix="sell_page"
        )
        await query.edit_message_text(
            f"💸 Sold {animal['emoji']} *{name}* for *{sell_price}* 🪙\n\nSell another?",
            reply_markup=kb,
            parse_mode="Markdown",
        )
    else:
        ctx.user_data.pop("sell_msg", None)
        await query.edit_message_text(
            f"💸 Sold {animal['emoji']} *{name}* for *{sell_price}* 🪙",
            parse_mode="Markdown",
        )


async def sell_cancel_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ctx.user_data.pop("sell_msg", None)
    await query.answer("Cancelled")
    await query.edit_message_text("Sell cancelled.")


async def sell_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    page = int(query.data.removeprefix("sell_page_"))

    animals = db.get_animals(tg_id)
    kb = animal_picker_keyboard(
        animals, "sell_pick", "sell_cancel", page=page, page_callback_prefix="sell_page"
    )
    await query.answer()
    await query.edit_message_text("Which animal do you want to sell?", reply_markup=kb)
