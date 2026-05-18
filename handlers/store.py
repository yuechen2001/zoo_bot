from telegram import Update
from telegram.ext import ContextTypes
import db
from game.achievements import check_achievements
from game.store_data import STORE_ITEMS, ITEMS, LURES, COSMETICS
from keyboards import store_tab_keyboard, store_welcome_keyboard

_ACTIVE_FLAGS = {
    "lucky_token": "lucky_catch_active",
    "mood_booster": "mood_booster_active",
    "catch_net": "catch_net_active",
}


def _store_section_text(section: str, tg_id: int) -> str:
    counts = db.get_item_counts(tg_id)
    user = db.get_user(tg_id)

    if section == "items":
        lines = [
            "🏪 <b>Zoo Store — Items</b>\n",
            "<i>Sit in your bag until used via /inventory.</i>\n",
        ]
        for key, item in ITEMS.items():
            line = f"  {item['emoji']} <b>{item['name']}</b> — {item['price']} 🪙\n  {item['desc']}"
            badges = []
            n = counts.get(key, 0)
            if n:
                badges.append(f"×{n} in bag")
            flag_col = _ACTIVE_FLAGS.get(key)
            if flag_col and user and user[flag_col]:
                badges.append("active")
            if badges:
                line += f"  <i>({', '.join(badges)})</i>"
            lines.append(line)
    elif section == "lures":
        lines = [
            "🏪 <b>Zoo Store — Lures</b> 🎣\n",
            "<i>Each /catch requires a lure. Habitat lures give 1.5× catch rate.</i>\n",
        ]
        for key, item in LURES.items():
            line = f"  {item['emoji']} <b>{item['name']}</b> — {item['price']} 🪙\n  {item['desc']}"
            n = counts.get(key, 0)
            if n:
                line += f"  <i>(×{n} in bag)</i>"
            lines.append(line)
    else:  # titles
        lines = [
            "🏪 <b>Zoo Store — Titles</b>\n",
            "<i>Shown next to your zoo name. Equip from /inventory.</i>\n",
        ]
        for key, item in COSMETICS.items():
            lines.append(
                f"  {item['emoji']} <b>{item['name']}</b> — {item['price']} 🪙\n  {item['desc']}"
            )

    return "\n".join(lines)


def _store_text(tg_id: int) -> str:
    """Legacy full-store text — kept for tests."""
    counts = db.get_item_counts(tg_id)
    user = db.get_user(tg_id)
    lines = ["🏪 <b>Zoo Store</b>\n"]
    lines.append("<b>Items</b> (sit in your bag until used):")
    for key, item in ITEMS.items():
        line = f"  {item['emoji']} <b>{item['name']}</b> — {item['price']} 🪙\n  {item['desc']}"
        badges = []
        n = counts.get(key, 0)
        if n:
            badges.append(f"×{n} in bag")
        flag_col = _ACTIVE_FLAGS.get(key)
        if flag_col and user and user[flag_col]:
            badges.append("active")
        if badges:
            line += f"  <i>({', '.join(badges)})</i>"
        lines.append(line)
    lines.append("\n<b>Lures</b> 🎣 (catching now requires a lure — select via /catch):")
    for key, item in LURES.items():
        line = f"  {item['emoji']} <b>{item['name']}</b> — {item['price']} 🪙\n  {item['desc']}"
        n = counts.get(key, 0)
        if n:
            line += f"  <i>(×{n} in bag)</i>"
        lines.append(line)
    lines.append("\n<b>Titles</b> (shown in your /zoo):")
    for key, item in COSMETICS.items():
        lines.append(
            f"  {item['emoji']} <b>{item['name']}</b> — {item['price']} 🪙\n  {item['desc']}"
        )
    lines.append("\nTap a button to buy. Use /inventory to use items and equip titles.")
    return "\n".join(lines)


async def store_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if not args or args[0].lower() != "buy":
        await update.message.reply_text(
            "🏪 <b>Welcome to the Zoo Store!</b>\n\n" "What are you looking for?",
            parse_mode="HTML",
            reply_markup=store_welcome_keyboard(),
        )
        return

    if len(args) < 2:
        await update.message.reply_text("Usage: `/store buy <item_key>`", parse_mode="Markdown")
        return
    await _buy(update, tg_id, user, args[1].lower())


async def store_tab_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    section = query.data.removeprefix("store_tab_")
    owned = db.get_owned_title_keys(tg_id)
    counts = db.get_item_counts(tg_id)
    try:
        await query.edit_message_text(
            _store_section_text(section, tg_id),
            parse_mode="HTML",
            reply_markup=store_tab_keyboard(section, owned, counts),
        )
    except Exception:
        pass
    await query.answer()


async def store_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    key = query.data.removeprefix("store_buy_")
    item = STORE_ITEMS.get(key)
    if not item:
        await query.answer("Unknown item.", show_alert=True)
        return

    if user["coins"] < item["price"]:
        await query.answer(
            f"Not enough coins! {item['name']} costs {item['price']} 🪙 (you have {user['coins']} 🪙).",
            show_alert=True,
        )
        return

    if item["category"] == "cosmetic":
        if db.has_purchased(tg_id, key):
            await query.answer(f"You already own {item['name']}! Use /inventory to equip it.")
            return
        db.deduct_coins(tg_id, item["price"])
        db.record_purchase(tg_id, key)
        owned = db.get_owned_title_keys(tg_id)
        counts = db.get_item_counts(tg_id)
        await query.answer(
            f"✅ Purchased {item['emoji']} {item['name']}! Use /inventory to equip it."
        )
        try:
            await query.edit_message_text(
                _store_section_text("titles", tg_id),
                parse_mode="HTML",
                reply_markup=store_tab_keyboard("titles", owned, counts),
            )
        except Exception:
            pass
        return

    db.deduct_coins(tg_id, item["price"])
    db.record_purchase(tg_id, key)
    if key.startswith("lure_"):
        msg = f"✅ {item['emoji']} {item['name']} added to your bag! Use /catch to apply it."
    else:
        msg = f"✅ {item['emoji']} {item['name']} added to your bag! Use /inventory to activate it."
    await query.answer(msg, show_alert=True)
    await check_achievements(tg_id, "store", ctx)


async def _buy(update, tg_id: int, user, item_key: str):
    item = STORE_ITEMS.get(item_key)
    if not item:
        await update.message.reply_text(
            f"Unknown item `{item_key}`. Use `/store` to see available items.",
            parse_mode="Markdown",
        )
        return

    if user["coins"] < item["price"]:
        await update.message.reply_text(
            f"Not enough coins! *{item['name']}* costs {item['price']} 🪙 "
            f"(you have {user['coins']} 🪙).",
            parse_mode="Markdown",
        )
        return

    if item["category"] == "cosmetic":
        if db.has_purchased(tg_id, item_key):
            await update.message.reply_text(
                f"You already own *{item['name']}*! Use `/inventory equip {item_key}` to wear it.",
                parse_mode="Markdown",
            )
            return
        db.deduct_coins(tg_id, item["price"])
        db.record_purchase(tg_id, item_key)
        await update.message.reply_text(
            f"✅ Purchased {item['emoji']} *{item['name']}*!\n"
            f"Use `/inventory equip {item_key}` to display it in your zoo.",
            parse_mode="Markdown",
        )
        return

    db.deduct_coins(tg_id, item["price"])
    db.record_purchase(tg_id, item_key)
    if item_key.startswith("lure_"):
        await update.message.reply_text(
            f"✅ {item['emoji']} *{item['name']}* added to your bag!\n"
            f"Run /catch to pick your lure and start hunting.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"✅ {item['emoji']} *{item['name']}* added to your bag!\n"
            f"Use `/inventory use {item_key}` to activate it.",
            parse_mode="Markdown",
        )
