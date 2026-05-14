from telegram import Update
from telegram.ext import ContextTypes
import db

FEED_COST = 10
FEED_HUNGER = 40
FEED_HAPPINESS = 10


async def feed_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: /feed <number>\nExample: /feed 1")
        return

    position = int(ctx.args[0])
    animal = db.get_animal_by_position(tg_id, position)

    if not animal:
        animals = db.get_animals(tg_id)
        await update.message.reply_text(
            f"No animal at position {position}. You have {len(animals)} animal(s)."
        )
        return

    if animal["is_breeding"]:
        await update.message.reply_text(
            f"{animal['emoji']} *{animal['nickname'] or animal['species_name']}* is currently breeding and can't be fed!",
            parse_mode="Markdown",
        )
        return

    if user["coins"] < FEED_COST:
        await update.message.reply_text(f"Not enough coins! Feeding costs {FEED_COST} 🪙.")
        return

    new_hunger = min(100, animal["hunger"] + FEED_HUNGER)
    new_happiness = min(100, animal["happiness"] + FEED_HAPPINESS)

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = coins - ? WHERE user_id = ?",
            (FEED_COST, tg_id),
        )
        conn.execute(
            "UPDATE animals SET hunger = ?, happiness = ? WHERE animal_id = ?",
            (new_hunger, new_happiness, animal["animal_id"]),
        )

    name = animal["nickname"] or animal["species_name"]
    await update.message.reply_text(
        f"🍖 Fed {animal['emoji']} *{name}*!\n\n"
        f"Hunger: {animal['hunger']} → {new_hunger}\n"
        f"Happiness: {animal['happiness']} → {new_happiness}\n"
        f"Cost: -{FEED_COST} 🪙",
        parse_mode="Markdown",
    )
