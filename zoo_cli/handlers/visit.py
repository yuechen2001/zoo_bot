import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db
from game.species_data import HABITATS, RARITY_SQUARE, RARITY_ORDER
from game.constants import (
    FEED_COST_BY_RARITY,
    FEED_HUNGER,
    VISIT_FEED_BONUS,
    VISIT_FEED_COOLDOWN_HOURS,
)
from utils import replace_command_ui


def _render_visit_zoo(username: str, animals: list) -> str:
    if not animals:
        return f"🏕 *{username}'s Zoo* — Empty\n\n_No animals yet!_"

    by_habitat: dict[str, dict] = {}
    for a in animals:
        h = a["habitat"] or "woodland"
        by_habitat.setdefault(h, {}).setdefault(a["species_id"], []).append(a)

    lines = [f"🏕 *{username}'s Zoo*\n"]
    for habitat_key, species_groups in by_habitat.items():
        h_info = HABITATS.get(habitat_key, {"emoji": "🏕", "name": habitat_key.title()})
        count = sum(len(v) for v in species_groups.values())
        lines.append(f"{h_info['emoji']} *{h_info['name']}*  ({count})")
        sorted_groups = sorted(
            species_groups.items(),
            key=lambda item: (
                (
                    RARITY_ORDER.index(item[1][0]["rarity"])
                    if item[1][0]["rarity"] in RARITY_ORDER
                    else 99
                ),
                item[1][0]["species_name"],
            ),
        )
        for _sid, members in sorted_groups:
            first = members[0]
            rarity_sq = RARITY_SQUARE.get(first["rarity"], "⬜")
            tag = f"  ×{len(members)}" if len(members) > 1 else ""
            lines.append(f"  {first['emoji']} {first['species_name']}  {rarity_sq}{tag}")

    return "\n".join(lines)


def _visit_keyboard(host_id: int, can_feed: bool) -> InlineKeyboardMarkup:
    if not can_feed:
        return InlineKeyboardMarkup([])
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🍖 Feed an animal", callback_data=f"visit_feed_{host_id}")]]
    )


async def visit_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    visitor = db.get_user(tg_id)
    if not visitor:
        await update.message.reply_text("Use /start first!")
        return

    if not ctx.args:
        msg = await update.message.reply_text("Usage: /visit @username")
        await replace_command_ui(ctx, "visit_ui", update, msg)
        return

    raw = ctx.args[0].lstrip("@")
    host = db.get_user_by_username(raw)
    if not host:
        msg = await update.message.reply_text(f"User @{raw} not found or hasn't started yet.")
        await replace_command_ui(ctx, "visit_ui", update, msg)
        return

    host_id = host["user_id"]
    if host_id == tg_id:
        msg = await update.message.reply_text("You can't visit your own zoo — use /zoo for that.")
        await replace_command_ui(ctx, "visit_ui", update, msg)
        return

    animals = db.get_animals(host_id)
    text = _render_visit_zoo(host["username"] or raw, animals)

    last_feed = db.get_last_visit_feed(tg_id, host_id)
    can_feed = True
    if last_feed:
        last_at = datetime.datetime.fromisoformat(last_feed["fed_at"])
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=datetime.timezone.utc)
        elapsed = datetime.datetime.now(datetime.timezone.utc) - last_at
        can_feed = elapsed.total_seconds() >= VISIT_FEED_COOLDOWN_HOURS * 3600

    if not animals:
        can_feed = False

    msg = await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=_visit_keyboard(host_id, can_feed),
    )
    await replace_command_ui(ctx, "visit_ui", update, msg)


async def visit_feed_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    host_id = int(query.data.removeprefix("visit_feed_"))

    visitor = db.get_user(tg_id)
    if not visitor:
        await query.answer("Use /start first!", show_alert=True)
        return

    last_feed = db.get_last_visit_feed(tg_id, host_id)
    if last_feed:
        last_at = datetime.datetime.fromisoformat(last_feed["fed_at"])
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=datetime.timezone.utc)
        elapsed = datetime.datetime.now(datetime.timezone.utc) - last_at
        if elapsed.total_seconds() < VISIT_FEED_COOLDOWN_HOURS * 3600:
            remaining = VISIT_FEED_COOLDOWN_HOURS * 3600 - elapsed.total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await query.answer(f"Cooldown: {hours}h {minutes}m remaining.", show_alert=True)
            return

    host_animals = db.get_animals(host_id)
    if not host_animals:
        await query.answer("Their zoo is empty!", show_alert=True)
        return

    hungry_animals = [a for a in host_animals if a["hunger"] < 100]
    if not hungry_animals:
        await query.answer("All animals are fully fed already!", show_alert=True)
        return

    target = min(hungry_animals, key=lambda a: a["hunger"])
    feed_cost = FEED_COST_BY_RARITY.get(target["rarity"], 5)

    if visitor["coins"] < feed_cost:
        await query.answer(
            f"Not enough coins! Costs {feed_cost} 🪙 (you have {visitor['coins']}).",
            show_alert=True,
        )
        return

    new_hunger = min(100, target["hunger"] + FEED_HUNGER)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    db.feed_animal(tg_id, target["animal_id"], new_hunger, feed_cost)
    db.add_coins(tg_id, VISIT_FEED_BONUS)
    db.record_visit_feed(tg_id, host_id, now)

    animal_name = target["nickname"] or target["species_name"]
    await query.answer(
        f"Fed {target['emoji']} {animal_name}! -{feed_cost} 🪙 +{VISIT_FEED_BONUS} 🪙 bonus.",
        show_alert=True,
    )
    await query.edit_message_reply_markup(reply_markup=_visit_keyboard(host_id, False))
