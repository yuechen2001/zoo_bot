import random
from telegram import Update
from telegram.ext import ContextTypes
import datetime
import db
from game.mood_engine import streak_label
from species_data import HABITATS, ENCLOSURE_LEVELS
from keyboards import zoo_page_keyboard
from config import INVESTMENT_HOURS


def _time_remaining(ready_at_str: str) -> str:
    ready = datetime.datetime.fromisoformat(ready_at_str)
    delta = ready - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
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

RARITY_ORDER = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}


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


def _get_breeding_ids(user_id: int) -> set:
    return db.get_breeding_animal_ids(user_id)


def _group_by_habitat(animals: list) -> dict[str, dict]:
    habitat_order = list(HABITATS.keys())
    by_habitat: dict[str, dict] = {h: {} for h in habitat_order}
    for a in animals:
        h = a["habitat"] or "woodland"
        sid = a["species_id"]
        if sid not in by_habitat[h]:
            by_habitat[h][sid] = []
        by_habitat[h][sid].append(a)
    return by_habitat


def _render_habitat_section(
    habitat_key: str,
    species_groups: dict,
    position: dict,
    breeding_ids: set,
    enclosures: dict,
) -> list[str]:
    h_info = HABITATS[habitat_key]
    level = enclosures.get(habitat_key, 1)
    total_in_habitat = sum(len(v) for v in species_groups.values())
    capacity = ENCLOSURE_LEVELS[level]["capacity"]

    lines = [f"{h_info['emoji']} *{h_info['name']}* [Lv {level}]  {total_in_habitat}/{capacity}"]

    sorted_groups = sorted(
        species_groups.items(),
        key=lambda item: (RARITY_ORDER.get(item[1][0]["rarity"], 99), item[1][0]["species_name"]),
    )

    for sid, members in sorted_groups:
        first = members[0]
        rarity_sq = RARITY_SQUARE.get(first["rarity"], "⬜")
        count = len(members)

        count_tag = f"  ×{count}" if count > 1 else ""
        lines.append(f"  *{first['emoji']} {first['species_name']}*  {rarity_sq}{count_tag}")

        for a in sorted(members, key=lambda x: x["animal_id"]):
            pos = position[a["animal_id"]]
            name = a["nickname"] or a["species_name"]
            lock = "  🔒" if a["animal_id"] in breeding_ids else ""
            lines.append(f"    #{pos} {name} — 🍖 {a['hunger']}{lock}")

    return lines


def render_zoo_page(
    username: str,
    animals: list,
    coins: int,
    streak: int,
    page: int = 0,
    autofeed_threshold=None,
    autofeed_max_coins=None,
    investment=None,
    active_breed=None,
    active_title: str | None = None,
) -> tuple[str, list[str]]:
    """
    Returns (rendered_text, inhabited_habitat_keys).
    inhabited_habitat_keys is needed to build the pagination keyboard.
    """
    if not animals:
        text = (
            f"🏕 *{username}'s Zoo* — Empty\n\n"
            f"_No animals yet!_\nUse /catch to find one.\n\n"
            f"💰 {coins} coins"
        )
        return text, []

    user_id = animals[0]["user_id"]
    breeding_ids = _get_breeding_ids(user_id)
    enclosures = db.get_enclosures(user_id)
    position = {a["animal_id"]: i + 1 for i, a in enumerate(animals)}

    by_habitat = _group_by_habitat(animals)
    inhabited = [h for h in HABITATS.keys() if by_habitat[h]]

    page = max(0, min(page, len(inhabited) - 1))
    habitat_key = inhabited[page]
    species_groups = by_habitat[habitat_key]

    if active_title:
        from game.store_data import COSMETICS

        title_item = COSMETICS.get(active_title)
        title_str = f"{title_item['emoji']} {title_item['name']} • " if title_item else ""
    else:
        title_str = ""

    lines = [f"🏕 {title_str}*{username}'s Zoo*\n"]
    lines.extend(
        _render_habitat_section(habitat_key, species_groups, position, breeding_ids, enclosures)
    )
    lines.append("")
    lines.append(f"💰 {coins} | {streak_label(streak)}")

    if autofeed_threshold is not None:
        lines.append(
            f"🤖 Auto-feed: ≤{autofeed_threshold} hunger | {autofeed_max_coins}🪙 per tick"
        )

    if investment:
        invested_at = datetime.datetime.fromisoformat(investment["invested_at"])
        matures_at = (invested_at + datetime.timedelta(hours=INVESTMENT_HOURS)).isoformat()
        inv_time = _time_remaining(matures_at)
        lines.append(
            f"💹 Investment: {investment['amount']} 🪙 → {investment['return_amount']} 🪙 ({inv_time})"
        )

    if active_breed:
        breed_time = _time_remaining(active_breed["ready_at"])
        lines.append(
            f"🥚 Breeding: {active_breed['emoji_a']} × {active_breed['emoji_b']} | {breed_time}"
        )

    return "\n".join(lines), inhabited


# kept for backward-compat with existing unit tests that import render_zoo directly
def render_zoo(username: str, animals: list, coins: int, streak: int) -> str:
    text, _ = render_zoo_page(username, animals, coins, streak, page=0)
    return text


async def zoo_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    animals = db.get_animals(tg_id)
    investment = db.get_active_investment(tg_id)
    active_breed = db.get_active_breed(tg_id)
    text, inhabited = render_zoo_page(
        update.effective_user.first_name,
        animals,
        user["coins"],
        user["streak_windows"],
        page=0,
        autofeed_threshold=user["autofeed_threshold"],
        autofeed_max_coins=user["autofeed_max_coins"],
        investment=investment,
        active_breed=active_breed,
        active_title=user["active_title"],
    )
    kb = zoo_page_keyboard(tg_id, 0, inhabited) if inhabited else None
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def zoo_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data  # "zoo_page_{owner_id}_{page}"

    rest = data[len("zoo_page_") :]
    owner_id_str, page_str = rest.rsplit("_", 1)
    owner_id = int(owner_id_str)
    page = int(page_str)

    if query.from_user.id != owner_id:
        await query.answer("Use /zoo to see your own zoo.", show_alert=False)
        return

    await query.answer()

    user = db.get_user(owner_id)
    animals = db.get_animals(owner_id)
    investment = db.get_active_investment(owner_id)
    active_breed = db.get_active_breed(owner_id)
    text, inhabited = render_zoo_page(
        query.from_user.first_name,
        animals,
        user["coins"],
        user["streak_windows"],
        page=page,
        autofeed_threshold=user["autofeed_threshold"],
        autofeed_max_coins=user["autofeed_max_coins"],
        investment=investment,
        active_breed=active_breed,
        active_title=user["active_title"],
    )
    kb = zoo_page_keyboard(owner_id, page, inhabited) if inhabited else None
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
