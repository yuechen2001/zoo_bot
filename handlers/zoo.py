from telegram import Update
from telegram.ext import ContextTypes
import datetime
import db
from game.mood_engine import streak_label


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
    """Fill tiles left-to-right: breeding animals show 💤, then normal, then borders."""
    tiles = []
    placed = 0
    for i in range(ROW_LEN):
        if placed < breeding_count:
            tiles.append("💤")
            placed += 1
        elif placed < count:
            tiles.append(animal_emoji)
            placed += 1
        else:
            tiles.append(BORDER_A if i % 2 == 0 else BORDER_B)
    return "".join(tiles)


def render_zoo(username: str, animals: list, coins: int, streak: int) -> str:
    if not animals:
        return (
            f"🏕 *{username}'s Zoo* — Empty\n\n"
            f"_No animals yet!_\nUse /catch to find one.\n\n"
            f"💰 {coins} coins"
        )

    # Build breeding set and position map from the ordered list
    breeding_ids = set()
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT parent_a, parent_b FROM breeding_queue WHERE user_id = ? AND collected = 0",
            (animals[0]["user_id"],),
        ).fetchall()
        for r in rows:
            breeding_ids.add(r["parent_a"])
            breeding_ids.add(r["parent_b"])

    position = {a["animal_id"]: i + 1 for i, a in enumerate(animals)}

    # Group by species_id preserving first-seen order
    species_order = []
    groups = {}
    for a in animals:
        sid = a["species_id"]
        if sid not in groups:
            species_order.append(sid)
            groups[sid] = []
        groups[sid].append(a)

    lines = [f"🏕 *{username}'s Zoo*\n"]

    for sid in species_order:
        members = groups[sid]
        first = members[0]
        rarity_sq = RARITY_SQUARE.get(first["rarity"], "⬜")
        count = len(members)
        breeding_in_group = sum(1 for a in members if a["animal_id"] in breeding_ids)

        count_tag = f"  ×{count}" if count > 1 else ""
        lines.append(f"*{first['emoji']} {first['species_name']}*  {rarity_sq}{count_tag}")
        lines.append(_render_habitat(first["emoji"], count, breeding_in_group))

        for a in members:
            pos = position[a["animal_id"]]
            name = a["nickname"] or a["species_name"]
            lock = "  🔒" if a["animal_id"] in breeding_ids else ""
            lines.append(f"  #{pos} {name} — 🍖 {a['hunger']}{lock}")

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
