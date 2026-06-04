import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db
from game.constants import BREED_BOOST_HOURS, INCOME_BOOST_HOURS, STORE_ITEMS_PAGE_SIZE
from game.store_data import ITEMS, LURES, COSMETICS
from utils import replace_command_ui

_NO_ARG_USABLE = {
    "lucky_token",
    "mood_booster",
    "catch_net",
    "breed_boost",
    "rare_magnet",
    "epic_magnet",
    "streak_shield",
    "breed_accelerator",
    "instant_hatch",
    "income_boost",
    "quest_task_skip",
}

_ACTIVE_FLAGS = {
    "lucky_token": "lucky_catch_active",
    "mood_booster": "mood_booster_active",
    "catch_net": "catch_net_active",
    "rare_magnet": "rare_magnet_active",
    "epic_magnet": "epic_magnet_active",
    "streak_shield": "streak_shield_active",
}


def _tab_keyboard(
    active: str, items_count: int, lures_count: int, titles_count: int, page: int = 0
) -> InlineKeyboardMarkup:
    def _label(section: str, count: int, display: str) -> str:
        prefix = "▶ " if section == active else ""
        return f"{prefix}{display} ({count})"

    nav = [
        InlineKeyboardButton(
            _label("items", items_count, "📦 Items"), callback_data="inv_tab_items_0"
        ),
        InlineKeyboardButton(
            _label("lures", lures_count, "🎣 Lures"), callback_data="inv_tab_lures"
        ),
        InlineKeyboardButton(
            _label("titles", titles_count, "🎭 Titles"), callback_data="inv_tab_titles"
        ),
    ]
    rows = [nav]

    if active == "items" and items_count > STORE_ITEMS_PAGE_SIZE:
        total_pages = (items_count + STORE_ITEMS_PAGE_SIZE - 1) // STORE_ITEMS_PAGE_SIZE
        pager = []
        if page > 0:
            pager.append(InlineKeyboardButton("◀", callback_data=f"inv_tab_items_{page - 1}"))
        pager.append(
            InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="inv_tab_items_0")
        )
        if page < total_pages - 1:
            pager.append(InlineKeyboardButton("▶", callback_data=f"inv_tab_items_{page + 1}"))
        rows.append(pager)

    return InlineKeyboardMarkup(rows)


def _render_overview(tg_id: int) -> tuple[str, InlineKeyboardMarkup]:
    counts = db.get_item_counts(tg_id)
    owned_titles = db.get_owned_title_keys(tg_id)

    items_in_bag = [(k, ITEMS[k], counts[k]) for k in ITEMS if counts.get(k, 0) > 0]
    lures_in_bag = [(k, LURES[k], counts[k]) for k in LURES if counts.get(k, 0) > 0]

    if not items_in_bag and not lures_in_bag and not owned_titles:
        return (
            "🎒 *Inventory*\n\n_Your bag is empty. Visit /store to buy items._",
            InlineKeyboardMarkup([]),
        )

    lines = ["🎒 *Inventory*\n"]
    if items_in_bag:
        total = sum(n for _, _, n in items_in_bag)
        lines.append(f"📦 *Consumables:* {len(items_in_bag)} type(s), {total} total")
    if lures_in_bag:
        total = sum(n for _, _, n in lures_in_bag)
        lines.append(f"🎣 *Lures:* {total} total")
    if owned_titles:
        lines.append(f"🎭 *Titles:* {len(owned_titles)} owned")
    lines.append("\n_Tap a tab to view details and use items._")

    kb = _tab_keyboard("overview", len(items_in_bag), len(lures_in_bag), len(owned_titles))
    return "\n".join(lines), kb


def _render_items_tab(tg_id: int, user, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    counts = db.get_item_counts(tg_id)
    items_in_bag = [(k, ITEMS[k], counts[k]) for k in ITEMS if counts.get(k, 0) > 0]
    owned_titles = db.get_owned_title_keys(tg_id)
    lure_types = sum(1 for k in LURES if counts.get(k, 0) > 0)

    total_pages = max(1, (len(items_in_bag) + STORE_ITEMS_PAGE_SIZE - 1) // STORE_ITEMS_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_items = items_in_bag[page * STORE_ITEMS_PAGE_SIZE : (page + 1) * STORE_ITEMS_PAGE_SIZE]

    if not items_in_bag:
        lines = ["🎒 *Consumables*\n\n_None in bag. Visit /store to buy items._"]
    else:
        lines = [f"🎒 *Consumables* ({page + 1}/{total_pages})\n"]
        for key, item, n in page_items:
            count_str = f" ×{n}" if n > 1 else ""
            flag = _ACTIVE_FLAGS.get(key)
            active = " _(active)_" if flag and user[flag] else ""
            lines.append(f"  {item['emoji']} *{item['name']}*{count_str}{active}")
            if key == "mega_feed":
                lines.append("    _→_ `/inventory use mega_feed <animal #>`")

    buttons = []
    for key, item, n in page_items:
        if key in _NO_ARG_USABLE:
            label = f"{item['emoji']} Use {item['name']}" + (f" ×{n}" if n > 1 else "")
            buttons.append([InlineKeyboardButton(label, callback_data=f"inv_use_{key}")])

    kb = _tab_keyboard("items", len(items_in_bag), lure_types, len(owned_titles), page)
    return "\n".join(lines), InlineKeyboardMarkup(list(kb.inline_keyboard) + buttons)


def _render_lures_tab(tg_id: int) -> tuple[str, InlineKeyboardMarkup]:
    counts = db.get_item_counts(tg_id)
    items_count = sum(1 for k in ITEMS if counts.get(k, 0) > 0)
    owned_titles = db.get_owned_title_keys(tg_id)
    lures_in_bag = [(k, LURES[k], counts[k]) for k in LURES if counts.get(k, 0) > 0]
    lure_types = len(lures_in_bag)

    if not lures_in_bag:
        lines = ["🎒 *Lures*\n\n_None in bag. Buy from /store._"]
    else:
        lines = ["🎒 *Lures* _(selected when you /catch):_\n"]
        for key, item, n in lures_in_bag:
            count_str = f" ×{n}" if n > 1 else ""
            lines.append(f"  {item['emoji']} *{item['name']}*{count_str}")

    kb = _tab_keyboard("lures", items_count, lure_types, len(owned_titles))
    return "\n".join(lines), kb


def _render_titles_tab(tg_id: int, user) -> tuple[str, InlineKeyboardMarkup]:
    counts = db.get_item_counts(tg_id)
    items_count = sum(1 for k in ITEMS if counts.get(k, 0) > 0)
    lure_types = sum(1 for k in LURES if counts.get(k, 0) > 0)
    owned_titles = db.get_owned_title_keys(tg_id)

    if not owned_titles:
        lines = ["🎒 *Titles*\n\n_None owned. Buy from /store._"]
        buttons = []
    else:
        active_title = user["active_title"]
        lines = ["🎒 *Titles:*\n"]
        buttons = []
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
                            callback_data=f"inv_equip_{key}",
                        )
                    ]
                )

    kb = _tab_keyboard("titles", items_count, lure_types, len(owned_titles))
    return "\n".join(lines), InlineKeyboardMarkup(list(kb.inline_keyboard) + buttons)


# Legacy single-render kept for tests that call _render directly.
def _render(tg_id: int, user) -> tuple[str, InlineKeyboardMarkup | None]:
    return _render_overview(tg_id)


async def inventory_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if not args:
        text, kb = _render_overview(tg_id)
        msg = await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
        await replace_command_ui(ctx, "inventory_ui", update, msg)
        return

    sub = args[0].lower()

    if sub == "use":
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: `/inventory use <item> [args]`", parse_mode="Markdown"
            )
            return
        item_key = args[1].lower()
        if item_key == "mega_feed":
            pos = int(args[2]) if len(args) > 2 and args[2].isdigit() else None
            if pos is None:
                await update.message.reply_text(
                    "Usage: `/inventory use mega_feed <animal number>`", parse_mode="Markdown"
                )
                return
            await _use_mega_feed(update, tg_id, pos)
        elif item_key in _NO_ARG_USABLE:
            msg = _apply(tg_id, item_key)
            await update.message.reply_text(msg, parse_mode="Markdown")
        elif item_key.startswith("lure_"):
            await update.message.reply_text(
                "Lures are used via /catch — just run /catch to pick your lure!"
            )
        else:
            await update.message.reply_text(
                f"Unknown item `{item_key}`. Use `/inventory` to see your bag.",
                parse_mode="Markdown",
            )

    elif sub == "equip":
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: `/inventory equip <title_key>`", parse_mode="Markdown"
            )
            return
        await _equip_title(update, tg_id, args[1].lower())

    else:
        text, kb = _render_overview(tg_id)
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def inventory_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    data = query.data

    if data.startswith("inv_tab_"):
        tab = data.removeprefix("inv_tab_")
        if tab.startswith("items_"):
            page = int(tab.removeprefix("items_")) if tab.removeprefix("items_").isdigit() else 0
            text, kb = _render_items_tab(tg_id, user, page)
        elif tab == "lures":
            text, kb = _render_lures_tab(tg_id)
        elif tab == "titles":
            text, kb = _render_titles_tab(tg_id, user)
        else:
            text, kb = _render_overview(tg_id)
        await query.answer()
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        except Exception:
            pass
        return

    if data.startswith("inv_equip_"):
        key = data.removeprefix("inv_equip_")
        msg = _equip_title_apply(tg_id, key)
        await query.answer(msg, show_alert=True)
    else:
        key = data.removeprefix("inv_use_")
        msg = _apply(tg_id, key)
        await query.answer(msg, show_alert=True)

    user = db.get_user(tg_id)
    text, kb = _render_items_tab(tg_id, user)
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
            datetime.datetime.fromisoformat(pending["ready_at"])
            - datetime.timedelta(hours=BREED_BOOST_HOURS),
        )
        db.adjust_breed_time_and_consume(pending["id"], new_ready.isoformat(), purchase["id"])
        return "⚡ Breed Boost applied! Breed time cut by 2 hours."

    if key == "rare_magnet":
        db.consume_purchase(purchase["id"])
        db.set_rare_magnet(tg_id, True)
        return "🧲 Rare Magnet activated! Your next /catch is guaranteed rare or higher."

    if key == "epic_magnet":
        db.consume_purchase(purchase["id"])
        db.set_epic_magnet(tg_id, True)
        return "💜 Epic Magnet activated! Your next /catch is guaranteed epic or higher."

    if key == "streak_shield":
        db.consume_purchase(purchase["id"])
        db.set_streak_shield(tg_id, True)
        return "🛡️ Streak Shield activated! Your streak is protected from the next miss."

    if key == "breed_accelerator":
        pending = db.get_pending_breed(tg_id)
        if not pending:
            return "No active breed to accelerate!"
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        ready_at = datetime.datetime.fromisoformat(pending["ready_at"])
        remaining = (ready_at - now).total_seconds()
        if remaining <= 0:
            return "Your breed is already ready — use /breed collect!"
        new_ready = now + datetime.timedelta(seconds=remaining / 2)
        db.adjust_breed_time_and_consume(pending["id"], new_ready.isoformat(), purchase["id"])
        return "🚀 Breed Accelerator applied! Remaining breed time halved."

    if key == "instant_hatch":
        pending = db.get_pending_breed(tg_id)
        if not pending:
            return "No active breed to hatch!"
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        db.adjust_breed_time_and_consume(pending["id"], now.isoformat(), purchase["id"])
        return "🐣 Breeding completed instantly! Use /breed collect."

    if key == "income_boost":
        expires = datetime.datetime.now(datetime.timezone.utc).replace(
            tzinfo=None
        ) + datetime.timedelta(hours=INCOME_BOOST_HOURS)
        db.set_income_boost(tg_id, expires.isoformat())
        db.consume_purchase(purchase["id"])
        return f"💰 Income Boost active for {INCOME_BOOST_HOURS} hours! Enclosure income doubled."

    if key == "quest_task_skip":
        from game.quests_data import CHAPTERS

        active_ch = db.get_active_chapter(tg_id)
        if not active_ch:
            return "No active quest chapter!"
        ch = CHAPTERS.get(active_ch)
        skipped = db.get_quest_tasks_skipped(tg_id, active_ch)
        if skipped >= len(ch["tasks"]) - 1:
            return "Can't skip any more tasks in this chapter — at least one must be completed naturally."
        db.increment_quest_tasks_skipped(tg_id, active_ch)
        db.consume_purchase(purchase["id"])
        return f"📜 Task skipped! One fewer task needed for Ch {active_ch}: *{ch['title']}*."

    return "Unknown item."


async def _use_mega_feed(update, tg_id: int, position: int):
    purchase = db.get_oldest_purchase(tg_id, "mega_feed")
    if not purchase:
        await update.message.reply_text(
            "You don't have a Mega Feed. Buy one with `/store buy mega_feed`.",
            parse_mode="Markdown",
        )
        return

    animal = db.get_animal_by_position(tg_id, position)
    if not animal:
        count = len(db.get_animals(tg_id))
        await update.message.reply_text(
            f"No animal at position #{position}. You have {count} animal(s)."
        )
        return

    db.feed_animal_and_consume(animal["animal_id"], purchase["id"])
    name = animal["nickname"] or animal["species_name"]
    await update.message.reply_text(
        f"🍖 *Mega Feed* applied! {animal['emoji']} *{name}* hunger restored to 100.",
        parse_mode="Markdown",
    )


def _equip_title_apply(tg_id: int, title_key: str) -> str:
    if title_key not in COSMETICS:
        return "Unknown title."
    if not db.has_purchased(tg_id, title_key):
        return "You don't own that title!"
    db.set_active_title(tg_id, title_key)
    item = COSMETICS[title_key]
    return f"{item['emoji']} Title set to *{item['name']}*! It'll appear in your /zoo."


async def _equip_title(update, tg_id: int, title_key: str):
    if title_key not in COSMETICS:
        await update.message.reply_text(
            "Unknown title. Use `/inventory` to see your titles.", parse_mode="Markdown"
        )
        return
    if not db.has_purchased(tg_id, title_key):
        item = COSMETICS[title_key]
        await update.message.reply_text(
            f"You don't own *{item['name']}* yet. Buy it for {item['price']} 🪙 with "
            f"`/store buy {title_key}`.",
            parse_mode="Markdown",
        )
        return
    db.set_active_title(tg_id, title_key)
    item = COSMETICS[title_key]
    await update.message.reply_text(
        f"{item['emoji']} Title set to *{item['name']}*! It'll appear in your /zoo.",
        parse_mode="Markdown",
    )
