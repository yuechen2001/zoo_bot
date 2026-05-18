from telegram import Update
from telegram.ext import ContextTypes
import db
from achievements import check_achievements
from species_data import HABITATS, ENCLOSURE_LEVELS, MAX_ENCLOSURE_LEVEL
from keyboards import enclosure_upgrade_keyboard


def _render_enclosures(user_id: int, coins: int) -> tuple[str, list[tuple[str, int]]]:
    """Return (message_text, list of (habitat_key, upgrade_cost) for upgradeable enclosures)."""
    enclosures = db.get_enclosures(user_id)
    lines = ["🏗 *Your Enclosures*\n"]
    upgradeable = []

    for habitat_key, h_info in HABITATS.items():
        level = enclosures.get(habitat_key, 1)
        stats = ENCLOSURE_LEVELS[level]
        used = db.get_animal_count_by_habitat(user_id, habitat_key)
        capacity = stats["capacity"]
        income = stats["coins_per_animal_hr"]
        bonus = stats["breed_bonus"]

        income_str = f"💰 {income * used}/hr" if income > 0 else "💰 0/hr"
        bonus_str = f"🧬 -{int(bonus * 100)}% breed time" if bonus > 0 else "🧬 no breed bonus"

        lines.append(
            f"{h_info['emoji']} *{h_info['name']}* \\[Lv {level}\\]  {used}/{capacity} animals"
        )
        lines.append(f"   {income_str}  •  {bonus_str}")

        if level < MAX_ENCLOSURE_LEVEL:
            next_cost = ENCLOSURE_LEVELS[level + 1]["upgrade_cost"]
            affordable = "✅" if coins >= next_cost else "❌"
            lines.append(f"   {affordable} Upgrade to Lv {level + 1}: {next_cost} 🪙")
            upgradeable.append((habitat_key, next_cost))
        else:
            lines.append("   ✨ Max level!")

        lines.append("")

    lines.append(f"💰 Your coins: *{coins}*")
    return "\n".join(lines), upgradeable


async def enclosures_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    if ctx.args and ctx.args[0].lower() == "collect":
        await _collect_income(update, tg_id)
        return

    # Existing players who predate enclosures get starter enclosures on first visit
    enclosures = db.get_enclosures(tg_id)
    if not enclosures:
        db.give_starter_enclosures(tg_id)

    text, upgradeable = _render_enclosures(tg_id, user["coins"])
    keyboard = enclosure_upgrade_keyboard(upgradeable) if upgradeable else None
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def _collect_income(update: Update, user_id: int):
    amount = db.collect_enclosure_coins(user_id)
    if amount == 0:
        await update.message.reply_text(
            "Nothing to collect yet — enclosure income builds up hourly.\n"
            "You'll get a notification when coins are ready."
        )
        return
    user = db.get_user(user_id)
    await update.message.reply_text(
        f"💰 Collected *{amount}* 🪙 from your enclosures!\nBalance: *{user['coins']}* 🪙",
        parse_mode="Markdown",
    )


async def enclosure_upgrade_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    habitat = query.data.removeprefix("enc_upgrade_")

    if habitat not in HABITATS:
        await query.answer("Unknown enclosure.", show_alert=True)
        return

    result = db.upgrade_enclosure(tg_id, habitat)

    if result == "max_level":
        await query.answer("Already at max level!", show_alert=True)
        return
    if result == "insufficient_coins":
        level = db.get_enclosure_level(tg_id, habitat)
        cost = ENCLOSURE_LEVELS[level + 1]["upgrade_cost"]
        await query.answer(f"Not enough coins! Need {cost} 🪙.", show_alert=True)
        return

    user = db.get_user(tg_id)
    text, upgradeable = _render_enclosures(tg_id, user["coins"])
    keyboard = enclosure_upgrade_keyboard(upgradeable) if upgradeable else None
    h_info = HABITATS[habitat]
    new_level = db.get_enclosure_level(tg_id, habitat)
    await query.answer(f"{h_info['emoji']} {h_info['name']} upgraded to Lv {new_level}!")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await check_achievements(tg_id, "enclosure", ctx)
