from telegram import Update
from telegram.ext import ContextTypes
import db
from game.species_data import HABITATS, RARITY_ORDER, RARITY_SQUARE


def _build_habitat_index(all_species: list) -> dict[str, list]:
    habitat_order = list(HABITATS.keys())
    by_habitat: dict[str, list] = {h: [] for h in habitat_order}
    for sp in all_species:
        h = sp["habitat"] or "woodland"
        if h in by_habitat:
            by_habitat[h].append(sp)
    return by_habitat


def render_directory_page(all_species: list, owned_ids: set, page: int) -> tuple[str, list[str]]:
    total = len(all_species)
    discovered = len(owned_ids)
    by_habitat = _build_habitat_index(all_species)

    habitat_keys = [h for h in HABITATS if by_habitat[h]]

    if not habitat_keys:
        return f"📖 *Animal Directory* — {discovered}/{total} discovered\n\n_No species found._", []

    page = max(0, min(page, len(habitat_keys) - 1))
    hab_key = habitat_keys[page]
    species_list = sorted(by_habitat[hab_key], key=lambda s: RARITY_ORDER.index(s["rarity"]))

    h_info = HABITATS[hab_key]
    hab_discovered = sum(1 for s in species_list if s["species_id"] in owned_ids)

    lines = [
        f"📖 *Animal Directory* — {discovered}/{total} discovered\n",
        f"{h_info['emoji']} *{h_info['name']}* — {hab_discovered}/{len(species_list)}",
    ]
    for sp in species_list:
        sq = RARITY_SQUARE.get(sp["rarity"], "⬜")
        status = "✅" if sp["species_id"] in owned_ids else "·"
        lines.append(f"  {sq} {sp['emoji']} {sp['name']}  {status}")

    return "\n".join(lines), habitat_keys


def render_directory(all_species: list, owned_ids: set) -> str:
    """Legacy full-list render — kept for tests and any internal callers."""
    total = len(all_species)
    discovered = len(owned_ids)
    by_habitat = _build_habitat_index(all_species)
    habitat_order = list(HABITATS.keys())

    lines = [f"📖 *Animal Directory* — {discovered}/{total} discovered\n"]
    for hab_key in habitat_order:
        species_list = by_habitat[hab_key]
        if not species_list:
            continue
        species_list.sort(key=lambda s: RARITY_ORDER.index(s["rarity"]))
        h_info = HABITATS[hab_key]
        hab_discovered = sum(1 for s in species_list if s["species_id"] in owned_ids)
        lines.append(f"{h_info['emoji']} *{h_info['name']}* — {hab_discovered}/{len(species_list)}")
        for sp in species_list:
            sq = RARITY_SQUARE.get(sp["rarity"], "⬜")
            status = "✅" if sp["species_id"] in owned_ids else "·"
            lines.append(f"  {sq} {sp['emoji']} {sp['name']}  {status}")
        lines.append("")

    return "\n".join(lines)


async def directory_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    from keyboards import directory_page_keyboard

    all_species = db.get_all_species()
    owned_ids = db.get_owned_species_ids(tg_id)
    text, habitat_keys = render_directory_page(all_species, owned_ids, 0)
    keyboard = directory_page_keyboard(tg_id, 0, habitat_keys) if len(habitat_keys) > 1 else None
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def directory_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")  # dir_page_{user_id}_{page}
    user_id = int(parts[2])
    page = int(parts[3])

    if query.from_user.id != user_id:
        await query.answer("Use /directory to browse your own progress.", show_alert=True)
        return

    all_species = db.get_all_species()
    owned_ids = db.get_owned_species_ids(user_id)
    text, habitat_keys = render_directory_page(all_species, owned_ids, page)
    from keyboards import directory_page_keyboard

    keyboard = (
        directory_page_keyboard(user_id, page, habitat_keys) if len(habitat_keys) > 1 else None
    )
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception:
        pass
