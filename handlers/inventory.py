import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db
from game.store_data import CONSUMABLES, LURES, COSMETICS

# Consumables that activate with no extra arguments
_NO_ARG_USABLE = {"lucky_token", "mood_booster", "catch_net", "breed_boost", "breed_accelerator"}

# Active-state flag columns for display
_ACTIVE_FLAGS = {
    "lucky_token": "lucky_catch_active",
    "mood_booster": "mood_booster_active",
    "catch_net": "catch_net_active",
}


def _render(tg_id: int, user) -> tuple[str, InlineKeyboardMarkup | None]:
    counts = db.get_consumable_counts(tg_id)
    owned_titles = db.get_owned_title_keys(tg_id)

    consumables_in_bag = [
        (k, CONSUMABLES[k], counts[k]) for k in CONSUMABLES if counts.get(k, 0) > 0
    ]
    lures_in_bag = [(k, LURES[k], counts[k]) for k in LURES if counts.get(k, 0) > 0]

    if not consumables_in_bag and not lures_in_bag and not owned_titles:
        return "🎒 *Inventory*\n\n_Your bag is empty. Visit /store to buy items._", None

    lines = ["🎒 *Inventory*\n"]
    buttons = []

    if consumables_in_bag:
        lines.append("*Consumables:*")
        for key, item, n in consumables_in_bag:
            count_str = f" ×{n}" if n > 1 else ""
            flag = _ACTIVE_FLAGS.get(key)
            active = " _(active)_" if flag and user[flag] else ""
            lines.append(f"  {item['emoji']} *{item['name']}*{count_str}{active}")
            if key == "mega_feed":
                lines.append("    _→_ `/store use mega_feed <animal #>`")
            elif key in _NO_ARG_USABLE:
                label = f"{item['emoji']} Use {item['name']}" + (f" ×{n}" if n > 1 else "")
                buttons.append([InlineKeyboardButton(label, callback_data=f"inv_use_{key}")])

    if lures_in_bag:
        lines.append("\n*Lures* _(selected when you /catch):_")
        for key, item, n in lures_in_bag:
            count_str = f" ×{n}" if n > 1 else ""
            lines.append(f"  {item['emoji']} *{item['name']}*{count_str}")

    if owned_titles:
        lines.append("\n*Titles:*")
        active_title = user["active_title"]
        for key in owned_titles:
            item = COSMETICS.get(key)
            if not item:
                continue
            equipped = " ✅" if key == active_title else ""
            lines.append(f"  {item['emoji']} *{item['name']}*{equipped}")
            if key != active_title:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"Equip {item['emoji']} {item['name']}",
                            callback_data=f"store_equip_{key}",
                        )
                    ]
                )

    kb = InlineKeyboardMarkup(buttons) if buttons else None
    return "\n".join(lines), kb


async def inventory_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    text, kb = _render(tg_id, user)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def inventory_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    key = query.data.removeprefix("inv_use_")

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    msg = _apply(tg_id, key)
    await query.answer(msg, show_alert=True)

    user = db.get_user(tg_id)
    text, kb = _render(tg_id, user)
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass


def _apply(tg_id: int, key: str) -> str:
    purchase = db.get_oldest_purchase(tg_id, key)
    if not purchase:
        return "You don't have that item anymore!"

    if key == "lucky_token":
        db.consume_purchase(purchase["id"])
        db.set_lucky_catch(tg_id, True)
        return "🎯 Lucky Token activated! Your next /catch has 2× catch rate."

    if key == "mood_booster":
        db.consume_purchase(purchase["id"])
        db.set_mood_booster(tg_id, True)
        return "✨ Mood Booster activated! Your next mood check-in earns double coins."

    if key == "catch_net":
        db.consume_purchase(purchase["id"])
        db.set_catch_net(tg_id, True)
        return "🪤 Catch Net activated! Your next /catch is guaranteed legendary."

    if key == "breed_boost":
        pending = db.get_pending_breed(tg_id)
        if not pending:
            return "No active breed to boost!"
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        new_ready = max(
            now,
            datetime.datetime.fromisoformat(pending["ready_at"]) - datetime.timedelta(hours=2),
        )
        db.adjust_breed_time_and_consume(pending["id"], new_ready.isoformat(), purchase["id"])
        return "⚡ Breed Boost applied! Breed time cut by 2 hours."

    if key == "breed_accelerator":
        pending = db.get_pending_breed(tg_id)
        if not pending:
            return "No active breed to accelerate!"
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        remaining = datetime.datetime.fromisoformat(pending["ready_at"]) - now
        new_ready = max(now, now + remaining / 2)
        db.adjust_breed_time_and_consume(pending["id"], new_ready.isoformat(), purchase["id"])
        return "🚀 Breed Accelerator applied! Remaining breed time halved."

    return "Unknown item."
