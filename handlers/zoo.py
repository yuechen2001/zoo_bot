import random
from telegram import Update
from telegram.ext import ContextTypes
import datetime
import db
from game.mood_engine import streak_label
from species_data import HABITATS, ENCLOSURE_LEVELS


def _time_remaining(ready_at_str: str) -> str:
    ready = datetime.datetime.fromisoformat(ready_at_str)
    delta = ready - datetime.datetime.utcnow()
    if delta.total_seconds() <= 0:
        return "ready!"
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


ROW_LEN = 9
BORDER_A = "🌿"
BORDER_B = "💧"

RARITY_SQUARE = {
    "common": "⬜",
    "rare": "🟦",
    "epic": "🟪",
    "legendary": "🟨",
}


def _render_habitat(animal_emoji: str, count: int, breeding_count: int) -> str:
    """Scatter animals randomly across the 9 tiles; breeding animals show 💤."""
    n = min(count, ROW_LEN)
    positions = random.sample(range(ROW_LEN), n)
    breeding_pos = set(positions[:breeding_count])
    normal_pos = set(positions[breeding_count:])

    border_idx = 0
    result = []
    for i in range(ROW_LEN):
        if i in breeding_pos:
            result.append("💤")
        elif i in normal_pos:
            result.append(animal_emoji)
        else:
            result.append(BORDER_A if border_idx % 2 == 0 else BORDER_B)
            border_idx += 1
    return "".join(result)


def render_zoo(username: str, animals: list, coins: int, streak: int) -> str:
    if not animals:
        return (
            f"🏕 *{username}'s Zoo* — Empty\n\n"
            f"_No animals yet!_\nUse /catch to find one.\n\n"
            f"💰 {coins} coins"
        )

    user_id = animals[0]["user_id"]

    # Build breeding set
    breeding_ids = set()
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT parent_a, parent_b FROM breeding_queue WHERE user_id = ? AND collected = 0",
            (user_id,),
        ).fetchall()
        for r in rows:
            breeding_ids.add(r["parent_a"])
            breeding_ids.add(r["parent_b"])

    enclosures = db.get_enclosures(user_id)  # {habitat: level}
    position = {a["animal_id"]: i + 1 for i, a in enumerate(animals)}

    # Group animals by habitat, then by species within
    habitat_order = list(HABITATS.keys())
    by_habitat: dict[str, dict] = {h: {} for h in habitat_order}
    for a in animals:
        h = a["habitat"] or "woodland"
        sid = a["species_id"]
        if sid not in by_habitat[h]:
            by_habitat[h][sid] = []
        by_habitat[h][sid].append(a)

    lines = [f"🏕 *{username}'s Zoo*\n"]

    for habitat_key in habitat_order:
        species_groups = by_habitat[habitat_key]
        if not species_groups:
            continue

        h_info = HABITATS[habitat_key]
        level = enclosures.get(habitat_key, 1)
        total_in_habitat = sum(len(v) for v in species_groups.values())
        capacity = ENCLOSURE_LEVELS[level]["capacity"]
        lines.append(
            f"{h_info['emoji']} *{h_info['name']}* \\[Lv {level}\\]  —  {total_in_habitat}/{capacity}"
        )

        for sid, members in species_groups.items():
            first = members[0]
            rarity_sq = RARITY_SQUARE.get(first["rarity"], "⬜")
            count = len(members)
            breeding_in_group = sum(1 for a in members if a["animal_id"] in breeding_ids)

            count_tag = f"  ×{count}" if count > 1 else ""
            lines.append(f"  *{first['emoji']} {first['species_name']}*  {rarity_sq}{count_tag}")
            lines.append(f"  {_render_habitat(first['emoji'], count, breeding_in_group)}")

            for a in members:
                pos = position[a["animal_id"]]
                name = a["nickname"] or a["species_name"]
                lock = "  🔒" if a["animal_id"] in breeding_ids else ""
                lines.append(f"    #{pos} {name} — 🍖 {a['hunger']}{lock}")

        lines.append("")

    lines.append(f"💰 {coins}  •  {streak_label(streak)}")
    return "\n".join(lines)


async def zoo_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    animals = db.get_animals(tg_id)
    text = render_zoo(
        update.effective_user.first_name,
        animals,
        user["coins"],
        user["streak_windows"],
    )
    await update.message.reply_text(text, parse_mode="Markdown")
