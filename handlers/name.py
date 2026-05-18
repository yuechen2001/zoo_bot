from telegram import Update
from telegram.ext import ContextTypes
import db
from keyboards import animal_picker_keyboard


async def name_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    ctx.user_data.pop("pending_name", None)

    if not ctx.args or len(ctx.args) < 2 or not ctx.args[0].isdigit():
        animals = db.get_animals(tg_id)
        if not animals:
            await update.message.reply_text("You have no animals to name.")
            return
        kb = animal_picker_keyboard(animals, "name_pick", "name_cancel")
        await update.message.reply_text("Which animal do you want to name?", reply_markup=kb)
        return

    position = int(ctx.args[0])
    nickname = " ".join(ctx.args[1:])[:20]
    animal = db.get_animal_by_position(tg_id, position)

    if not animal:
        count = len(db.get_animals(tg_id))
        await update.message.reply_text(f"No animal at #{position}. You have {count} animal(s).")
        return

    db.set_animal_nickname(animal["animal_id"], nickname)

    await update.message.reply_text(
        f"{animal['emoji']} Animal #{position} is now called *{nickname}*!",
        parse_mode="Markdown",
    )


async def name_pick_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    pos = int(query.data.removeprefix("name_pick_"))

    animal = db.get_animal_by_position(tg_id, pos)
    if not animal:
        await query.answer("That animal no longer exists.", show_alert=True)
        return

    name = animal["nickname"] or animal["species_name"]
    ctx.user_data["pending_name"] = {"pos": pos}

    await query.answer()
    await query.edit_message_text(
        f"{animal['emoji']} *{name}* selected.\n\nSend the new nickname (max 20 chars):",
        parse_mode="Markdown",
    )


async def name_cancel_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ctx.user_data.pop("pending_name", None)
    await query.answer("Cancelled")
    await query.edit_message_text("Naming cancelled.")


async def name_text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pending = ctx.user_data.get("pending_name")
    if not pending:
        return

    tg_id = update.effective_user.id
    pos = pending["pos"]
    nickname = update.message.text.strip()[:20]

    animal = db.get_animal_by_position(tg_id, pos)
    ctx.user_data.pop("pending_name", None)

    if not animal:
        await update.message.reply_text("That animal no longer exists.")
        return

    db.set_animal_nickname(animal["animal_id"], nickname)
    await update.message.reply_text(
        f"{animal['emoji']} *{nickname}* — name saved!",
        parse_mode="Markdown",
    )
