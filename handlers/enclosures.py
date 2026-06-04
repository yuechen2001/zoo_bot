from telegram import Update
from telegram.ext import ContextTypes
import db
from game.achievements import triggers
from game.species_data import HABITATS, ENCLOSURE_LEVELS, MAX_ENCLOSURE_LEVEL
from game.constants import ENC_PAGE_SIZE
from keyboards import enclosure_upgrade_keyboard

_HABITAT_KEYS = list(HABITATS.keys())
_TOTAL_ENC_PAGES = max(1, (len(_HABITAT_KEYS) + ENC_PAGE_SIZE - 1) // ENC_PAGE_SIZE)


def _render_enclosures(
    user_id: int, coins: int, page: int = 0
) -> tuple[str, list[tuple[str, int]]]:
    """Return (message_text, list of (habitat_key, upgrade_cost) for upgradeable enclosures on this page)."""
    enclosures = db.get_enclosures(user_id)
    start = page * ENC_PAGE_SIZE
    page_keys = _HABITAT_KEYS[start : start + ENC_PAGE_SIZE]

    lines = [f"🏗 *Your Enclosures* ({page + 1}/{_TOTAL_ENC_PAGES})\n"]
    upgradeable = []

    for habitat_key in page_keys:
        h_info = HABITATS[habitat_key]
        level = enclosures.get(habitat_key, 1)
        stats = ENCLOSURE_LEVELS[level]
        used = db.get_animal_count_by_habitat(user_id, habitat_key)
        capacity = stats["capacity"]
        income = stats["coins_per_animal_hr"]
        bonus = stats["breed_bonus"]
        catch_bonus = stats["catch_rate_bonus"]

        income_str = f"💰 {income * used}/hr" if income > 0 else "💰 0/hr"
        bonus_str = f"🧬 -{int(bonus * 100)}% breed time" if bonus > 0 else "🧬 no breed bonus"

        lines.append(
            f"{h_info['emoji']} *{h_info['name']}* \\[Lv {level}\\]  {used}/{capacity} animals"
        )
        lines.append(f"   {income_str}  •  {bonus_str}")
        if catch_bonus > 0:
            lines.append(f"   🎯 +{int(catch_bonus * 100)}% catch rate (lure)")

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

    # Existing players who predate enclosures get starter enclosures on first visit
    enclosures = db.get_enclosures(tg_id)
    if not enclosures:
        db.give_starter_enclosures(tg_id)

    text, upgradeable = _render_enclosures(tg_id, user["coins"], page=0)
    keyboard = enclosure_upgrade_keyboard(upgradeable, tg_id, page=0, total_pages=_TOTAL_ENC_PAGES)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


@triggers("enclosure")
async def enclosure_upgrade_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rest = query.data.removeprefix("enc_upgrade_")
    owner_id_str, _, habitat = rest.partition("_")
    owner_id = int(owner_id_str)

    if query.from_user.id != owner_id:
        await query.answer("Use /enclosures to manage your own enclosures.", show_alert=False)
        return

    tg_id = owner_id

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
    rest2 = query.data.removeprefix("enc_upgrade_")
    _, _, hab_key = rest2.partition("_")
    page = _HABITAT_KEYS.index(hab_key) // ENC_PAGE_SIZE if hab_key in _HABITAT_KEYS else 0
    text, upgradeable = _render_enclosures(tg_id, user["coins"], page=page)
    keyboard = enclosure_upgrade_keyboard(
        upgradeable, tg_id, page=page, total_pages=_TOTAL_ENC_PAGES
    )
    h_info = HABITATS[habitat]
    new_level = db.get_enclosure_level(tg_id, habitat)
    await query.answer(f"{h_info['emoji']} {h_info['name']} upgraded to Lv {new_level}!")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def enclosure_collect_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    owner_id = int(query.data.removeprefix("enc_collect_"))

    if query.from_user.id != owner_id:
        await query.answer("Use /enclosures to manage your own enclosures.", show_alert=False)
        return

    tg_id = owner_id

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    amount = db.collect_enclosure_coins(tg_id)
    if amount == 0:
        await query.answer("Nothing to collect yet — income builds up hourly.", show_alert=True)
        return

    user = db.get_user(tg_id)
    await query.answer(f"💰 Collected {amount} 🪙! Balance: {user['coins']} 🪙")
    text, upgradeable = _render_enclosures(tg_id, user["coins"], page=0)
    keyboard = enclosure_upgrade_keyboard(upgradeable, tg_id, page=0, total_pages=_TOTAL_ENC_PAGES)
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception:
        pass


async def enclosure_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rest = query.data.removeprefix("enc_page_")
    owner_id_str, _, page_str = rest.rpartition("_")
    owner_id = int(owner_id_str)

    if query.from_user.id != owner_id:
        await query.answer("Use /enclosures to manage your own enclosures.", show_alert=False)
        return

    page = max(0, min(int(page_str), _TOTAL_ENC_PAGES - 1))
    user = db.get_user(owner_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    text, upgradeable = _render_enclosures(owner_id, user["coins"], page=page)
    keyboard = enclosure_upgrade_keyboard(
        upgradeable, owner_id, page=page, total_pages=_TOTAL_ENC_PAGES
    )
    await query.answer()
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
