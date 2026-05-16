from telegram import Update
from telegram.ext import ContextTypes
import db
from achievements import check_achievements

FEED_COST_BY_RARITY = {"common": 5, "rare": 10, "epic": 15, "legendary": 20}
FEED_HUNGER = 40


async def feed_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    positions = [int(a) for a in (ctx.args or []) if a.isdigit()]
    if not positions:
        await update.message.reply_text("Usage: /feed <number> [number ...]\nExample: /feed 1 3 5")
        return

    lines = []
    for position in positions:
        animal = db.get_animal_by_position(tg_id, position)
        if not animal:
            lines.append(f"#{position}: no animal found")
            continue

        name = animal["nickname"] or animal["species_name"]

        if animal["is_breeding"]:
            lines.append(f"#{position}: {animal['emoji']} *{name}* is breeding, skipped")
            continue

        if animal["hunger"] >= 100:
            lines.append(f"#{position}: {animal['emoji']} *{name}* is already full!")
            continue

        feed_cost = FEED_COST_BY_RARITY.get(animal["rarity"], 10)
        user = db.get_user(tg_id)
        if user["coins"] < feed_cost:
            lines.append(f"#{position}: not enough coins (need {feed_cost} 🪙)")
            break

        new_hunger = min(100, animal["hunger"] + FEED_HUNGER)

        with db.get_conn() as conn:
            conn.execute(
                "UPDATE users SET coins = coins - ? WHERE user_id = ?",
                (feed_cost, tg_id),
            )
            conn.execute(
                "UPDATE animals SET hunger = ?, hunger_alerted = NULL WHERE animal_id = ?",
                (new_hunger, animal["animal_id"]),
            )

        lines.append(
            f"🍖 {animal['emoji']} *{name}*: hunger {animal['hunger']}→{new_hunger} (-{feed_cost} 🪙)"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    if any("🍖" in line for line in lines):
        await check_achievements(tg_id, "feed", ctx)
