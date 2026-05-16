import uuid
import random
from telegram import Update
from telegram.ext import ContextTypes
import db


async def start_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    tg_id = user.id
    username = user.username or user.first_name

    if chat.type == "private":
        await update.message.reply_text(
            "Hey! Add me to a group and use /start there. 🦁"
        )
        return

    db.ensure_user(tg_id, username, chat.id)

    animals = db.get_animals(tg_id)
    if animals:
        await update.message.reply_text(
            f"Welcome back, {username}! 🦁 Use /zoo to see your animals."
        )
        return

    # Give a random starter common animal
    with db.get_conn() as conn:
        commons = conn.execute(
            "SELECT * FROM species WHERE rarity = 'common'"
        ).fetchall()
        starter = random.choice(commons)
        animal_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO animals (animal_id, user_id, species_id) VALUES (?, ?, ?)",
            (animal_id, tg_id, starter["species_id"]),
        )

    await update.message.reply_text(
        f"Hey {username}! 🎉 Welcome to *Zoo Bot*!\n\n"
        f"You start with *100 coins* and a {starter['emoji']} *{starter['name']}*!\n\n"
        f"Mood prompts arrive every 30 min — respond to earn coins.\n"
        f"Spend coins to /catch more animals and /breed them.\n\n"
        f"/zoo — see your zoo\n"
        f"/catch — look for a wild animal\n"
        f"/help — all commands",
        parse_mode="Markdown",
    )
