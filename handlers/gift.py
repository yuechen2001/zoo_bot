from telegram import Update
from telegram.ext import ContextTypes
import db
from game.achievements import check_achievements
from game.species_data import ENCLOSURE_LEVELS
from utils import format_mention


async def gift_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    sender = db.get_user(tg_id)
    if not sender:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if len(args) != 2 or not args[0].isdigit():
        await update.message.reply_text(
            "Usage: `/gift <position> @username`\nExample: `/gift 3 @friend`",
            parse_mode="Markdown",
        )
        return

    position = int(args[0])
    username = args[1].lstrip("@")

    recipient = db.get_user_by_username(username)
    if not recipient:
        await update.message.reply_text(f"@{username} hasn't started the bot yet.")
        return

    if recipient["user_id"] == tg_id:
        await update.message.reply_text("You can't gift an animal to yourself!")
        return

    animal = db.get_animal_by_position(tg_id, position)
    if not animal:
        count = len(db.get_animals(tg_id))
        await update.message.reply_text(
            f"No animal at position #{position}. You have {count} animal(s)."
        )
        return

    if animal["is_breeding"]:
        await update.message.reply_text("That animal is currently breeding and can't be gifted.")
        return

    if db.has_pending_trade_for_animal(animal["animal_id"]):
        await update.message.reply_text("That animal has a pending trade offer. Cancel it first.")
        return

    habitat = animal["habitat"]
    enc_level = db.get_enclosure_level(recipient["user_id"], habitat)
    capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
    current_count = db.get_animal_count_by_habitat(recipient["user_id"], habitat)
    if current_count >= capacity:
        await update.message.reply_text(
            f"@{username}'s {habitat} enclosure is full (level {enc_level}, capacity {capacity})."
        )
        return

    db.transfer_animal(animal["animal_id"], recipient["user_id"])

    name = animal["nickname"] or animal["species_name"]
    sender_mention = format_mention(sender["username"], tg_id)
    chat_id = sender["group_chat_id"] or tg_id
    await ctx.bot.send_message(
        chat_id,
        f"🎁 *{sender_mention}* gifted {animal['emoji']} *{name}* to *@{username}*!",
        parse_mode="Markdown",
    )
    await check_achievements(tg_id, "gift", ctx)
