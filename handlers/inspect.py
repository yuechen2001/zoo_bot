from telegram import Update
from telegram.ext import ContextTypes
import db


def _stars(stat: int) -> str:
    """Convert 0–100 stat to a 5-star display."""
    filled = min(5, max(1, (stat + 10) // 20))
    return "★" * filled + "☆" * (5 - filled)


async def inspect_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text(
            "Usage: `/inspect <position>` — e.g. `/inspect 3`", parse_mode="Markdown"
        )
        return

    pos = int(ctx.args[0])
    animal = db.get_animal_by_position(tg_id, pos)
    if not animal:
        count = len(db.get_animals(tg_id))
        await update.message.reply_text(f"No animal at position {pos}. You have {count} animal(s).")
        return

    name = animal["nickname"] or animal["species_name"]
    speed = animal["stat_speed"] if "stat_speed" in animal.keys() else 50
    rarity_stat = animal["stat_rarity"] if "stat_rarity" in animal.keys() else 50
    temperament = animal["stat_temperament"] if "stat_temperament" in animal.keys() else 50

    await update.message.reply_text(
        f"🔬 *Inspect: {animal['emoji']} {name} #{pos}*\n\n"
        f"⚡ Speed:        {_stars(speed)}  _(shorter breed time)_\n"
        f"🌟 Genetics:     {_stars(rarity_stat)}  _(rarer offspring)_\n"
        f"🍖 Temperament:  {_stars(temperament)}  _(more enclosure income)_",
        parse_mode="Markdown",
    )
