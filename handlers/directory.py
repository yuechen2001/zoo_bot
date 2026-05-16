from telegram import Update
from telegram.ext import ContextTypes
import db
from species_data import HABITATS, RARITY_ORDER

RARITY_SQUARE = {
    "common": "⬜",
    "rare": "🟦",
    "epic": "🟪",
    "legendary": "🟨",
}


def render_directory(all_species: list, owned_ids: set) -> str:
    total = len(all_species)
    discovered = len(owned_ids)

    habitat_order = list(HABITATS.keys())
    by_habitat: dict[str, list] = {h: [] for h in habitat_order}
    for sp in all_species:
        h = sp["habitat"] or "woodland"
        if h in by_habitat:
            by_habitat[h].append(sp)

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

    all_species = db.get_all_species()
    owned_ids = db.get_owned_species_ids(tg_id)
    text = render_directory(all_species, owned_ids)
    await update.message.reply_text(text, parse_mode="Markdown")
