import random
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.mood_engine import streak_label

ROW_LEN = 9   # total tiles in the enclosure row
BORDER_A = "🌿"
BORDER_B = "💧"

RARITY_SQUARE = {
    "common":    "⬜",
    "rare":      "🟦",
    "epic":      "🟪",
    "legendary": "🟨",
}


def _render_habitat(animal_emoji: str, is_breeding: bool) -> str:
    """Single-row enclosure — animal placed at a random position."""
    pos = random.randint(0, ROW_LEN - 1)
    tiles = []
    for i in range(ROW_LEN):
        if i == pos:
            tiles.append("💤" if is_breeding else animal_emoji)
        else:
            tiles.append(BORDER_A if i % 2 == 0 else BORDER_B)
    return "".join(tiles)


def _happiness_face(hp: int) -> str:
    if hp >= 80: return "😄"
    if hp >= 60: return "🙂"
    if hp >= 40: return "😐"
    if hp >= 20: return "😟"
    return "😢"


def render_zoo(username: str, animals: list, coins: int, streak: int) -> str:
    if not animals:
        return (
            f"🏕 *{username}'s Zoo* — Empty\n\n"
            f"_No animals yet!_\nUse /catch to find one.\n\n"
            f"💰 {coins} coins"
        )

    breeding_ids = set()
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT parent_a, parent_b FROM breeding_queue WHERE user_id = ? AND collected = 0",
            (animals[0]["user_id"],),
        ).fetchall()
        for r in rows:
            breeding_ids.add(r["parent_a"])
            breeding_ids.add(r["parent_b"])

    lines = [f"🏕 *{username}'s Zoo*\n"]

    for i, a in enumerate(animals, 1):
        name = a["nickname"] or a["species_name"]
        is_breeding = a["animal_id"] in breeding_ids
        rarity_sq = RARITY_SQUARE.get(a["rarity"], "⬜")
        lock = "  🔒" if is_breeding else ""
        face = _happiness_face(a["happiness"])

        lines.append(
            f"*{i}. {a['emoji']} {name}* {rarity_sq}{lock}\n"
            f"{_render_habitat(a['emoji'], is_breeding)}\n"
            f"🍖 {a['hunger']}  {face} {a['happiness']}\n"
        )

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
