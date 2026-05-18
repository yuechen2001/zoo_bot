import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from achievements import check_achievements
from game.store_data import STORE_ITEMS, CONSUMABLES, LURES, COSMETICS
from keyboards import store_keyboard

# Maps consumable keys to the flag column that tracks "currently active" state
_ACTIVE_FLAGS = {
    "lucky_token": "lucky_catch_active",
    "mood_booster": "mood_booster_active",
    "catch_net": "catch_net_active",
}


def _store_text(tg_id: int) -> str:
    counts = db.get_consumable_counts(tg_id)
    user = db.get_user(tg_id)
    lines = ["🏪 *Zoo Store*\n"]
    lines.append("*Consumables* (sit in your bag until used):")
    for key, item in CONSUMABLES.items():
        line = f"  {item['emoji']} *{item['name']}* — {item['price']} 🪙\n  {item['desc']}"
        badges = []
        n = counts.get(key, 0)
        if n:
            badges.append(f"×{n} in bag")
        flag_col = _ACTIVE_FLAGS.get(key)
        if flag_col and user and user[flag_col]:
            badges.append("active")
        if badges:
            line += f"  _({', '.join(badges)})_"
        lines.append(line)
    lines.append("\n*Lures* 🎣 (catching now requires a lure — select via /catch):")
    for key, item in LURES.items():
        line = f"  {item['emoji']} *{item['name']}* — {item['price']} 🪙\n  {item['desc']}"
        n = counts.get(key, 0)
        if n:
            line += f"  _(×{n} in bag)_"
        lines.append(line)
    lines.append("\n*Titles* (shown in your /zoo):")
    for key, item in COSMETICS.items():
        lines.append(f"  {item['emoji']} *{item['name']}* — {item['price']} 🪙\n  {item['desc']}")
    lines.append(
        "\n_Tap a button to buy. Use_ `/store use <item>` _for consumables, or /catch for lures._"
    )
    return "\n".join(lines)


async def store_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if not args:
        owned = db.get_owned_title_keys(tg_id)
        counts = db.get_consumable_counts(tg_id)
        await update.message.reply_text(
            _store_text(tg_id), parse_mode="Markdown", reply_markup=store_keyboard(owned, counts)
        )
        return

    sub = args[0].lower()

    if sub == "buy":
        if len(args) < 2:
            await update.message.reply_text("Usage: `/store buy <item_key>`", parse_mode="Markdown")
            return
        await _buy(update, tg_id, user, args[1].lower())

    elif sub == "use":
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: `/store use <item> [args]`", parse_mode="Markdown"
            )
            return
        item_key = args[1].lower()
        if item_key == "mega_feed":
            pos = int(args[2]) if len(args) > 2 and args[2].isdigit() else None
            if pos is None:
                await update.message.reply_text(
                    "Usage: `/store use mega_feed <animal number>`", parse_mode="Markdown"
                )
                return
            await _use_mega_feed(update, tg_id, pos)
        elif item_key == "breed_boost":
            await _use_breed_boost(update, tg_id)
        elif item_key == "lucky_token":
            await _use_lucky_token(update, tg_id)
        elif item_key == "mood_booster":
            await _use_mood_booster(update, tg_id)
        elif item_key == "catch_net":
            await _use_catch_net(update, tg_id)
        elif item_key == "breed_accelerator":
            await _use_breed_accelerator(update, tg_id)
        elif item_key.startswith("lure_"):
            await update.message.reply_text(
                "Lures are used via /catch — just run /catch to pick your lure!"
            )
        else:
            await update.message.reply_text(
                f"Unknown item `{item_key}`. Use `/store` to see available items.",
                parse_mode="Markdown",
            )

    elif sub == "equip":
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: `/store equip <title_key>`", parse_mode="Markdown"
            )
            return
        await _equip_title(update, tg_id, args[1].lower())

    else:
        owned = db.get_owned_title_keys(tg_id)
        counts = db.get_consumable_counts(tg_id)
        await update.message.reply_text(
            _store_text(tg_id), parse_mode="Markdown", reply_markup=store_keyboard(owned, counts)
        )


async def store_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    data = query.data  # store_buy_{key} or store_equip_{key}

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    if data.startswith("store_equip_"):
        key = data.removeprefix("store_equip_")
        await query.answer()
        await _equip_title(query, tg_id, key)
        return

    key = data.removeprefix("store_buy_")
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

    # Cosmetic
    if item["category"] == "cosmetic":
        if db.has_purchased(tg_id, key):
            await query.answer(f"You already own {item['name']}! Tap Equip to wear it.")
            return
        db.deduct_coins(tg_id, item["price"])
        db.record_purchase(tg_id, key)
        owned = db.get_owned_title_keys(tg_id)
        counts = db.get_consumable_counts(tg_id)
        await query.answer(f"✅ Purchased {item['emoji']} {item['name']}! Tap Equip to wear it.")
        try:
            await query.edit_message_reply_markup(reply_markup=store_keyboard(owned, counts))
        except Exception:
            pass
        return

    # Consumables and lures — all go to inventory
    db.deduct_coins(tg_id, item["price"])
    db.record_purchase(tg_id, key)
    if key.startswith("lure_"):
        msg = f"✅ {item['emoji']} {item['name']} added to your bag! Use /catch to apply it."
    else:
        msg = f"✅ {item['emoji']} {item['name']} added to your bag! Use /store use {key} to activate."
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
                f"You already own *{item['name']}*! Use `/store equip {item_key}` to wear it.",
                parse_mode="Markdown",
            )
            return
        db.deduct_coins(tg_id, item["price"])
        db.record_purchase(tg_id, item_key)
        await update.message.reply_text(
            f"✅ Purchased {item['emoji']} *{item['name']}*!\n"
            f"Use `/store equip {item_key}` to display it in your zoo.",
            parse_mode="Markdown",
        )
        return

    # Consumables and lures — all go to inventory
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
            f"Use `/store use {item_key}` to activate it.",
            parse_mode="Markdown",
        )


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


async def _use_breed_boost(update, tg_id: int):
    purchase = db.get_oldest_purchase(tg_id, "breed_boost")
    if not purchase:
        await update.message.reply_text(
            "You don't have a Breed Boost. Buy one with `/store buy breed_boost`.",
            parse_mode="Markdown",
        )
        return

    pending = db.get_pending_breed(tg_id)
    if not pending:
        await update.message.reply_text("No active breed to boost!")
        return

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    new_ready = max(
        now, datetime.datetime.fromisoformat(pending["ready_at"]) - datetime.timedelta(hours=2)
    )
    db.adjust_breed_time_and_consume(pending["id"], new_ready.isoformat(), purchase["id"])
    await update.message.reply_text(
        "⚡ *Breed Boost* applied! Breed time cut by 2 hours.", parse_mode="Markdown"
    )


async def _use_lucky_token(update, tg_id: int):
    purchase = db.get_oldest_purchase(tg_id, "lucky_token")
    if not purchase:
        await update.message.reply_text(
            "You don't have a Lucky Token. Buy one with `/store buy lucky_token`.",
            parse_mode="Markdown",
        )
        return

    db.consume_purchase(purchase["id"])
    db.set_lucky_catch(tg_id, True)
    await update.message.reply_text(
        "🎯 *Lucky Token* activated! Your next /catch has 2× catch rate.", parse_mode="Markdown"
    )


async def _use_mood_booster(update, tg_id: int):
    purchase = db.get_oldest_purchase(tg_id, "mood_booster")
    if not purchase:
        await update.message.reply_text(
            "You don't have a Mood Booster. Buy one with `/store buy mood_booster`.",
            parse_mode="Markdown",
        )
        return

    db.consume_purchase(purchase["id"])
    db.set_mood_booster(tg_id, True)
    await update.message.reply_text(
        "✨ *Mood Booster* activated! Your next mood check-in earns double coins.",
        parse_mode="Markdown",
    )


async def _use_catch_net(update, tg_id: int):
    purchase = db.get_oldest_purchase(tg_id, "catch_net")
    if not purchase:
        await update.message.reply_text(
            "You don't have a Catch Net. Buy one with `/store buy catch_net`.",
            parse_mode="Markdown",
        )
        return

    db.consume_purchase(purchase["id"])
    db.set_catch_net(tg_id, True)
    await update.message.reply_text(
        "🪤 *Catch Net* activated! Your next /catch will encounter a legendary and is guaranteed to succeed.",
        parse_mode="Markdown",
    )


async def _use_breed_accelerator(update, tg_id: int):
    purchase = db.get_oldest_purchase(tg_id, "breed_accelerator")
    if not purchase:
        await update.message.reply_text(
            "You don't have a Breed Accelerator. Buy one with `/store buy breed_accelerator`.",
            parse_mode="Markdown",
        )
        return

    pending = db.get_pending_breed(tg_id)
    if not pending:
        await update.message.reply_text("No active breed to accelerate!")
        return

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    ready_at = datetime.datetime.fromisoformat(pending["ready_at"])
    remaining = ready_at - now
    new_ready = max(now, now + remaining / 2)
    db.adjust_breed_time_and_consume(pending["id"], new_ready.isoformat(), purchase["id"])
    await update.message.reply_text(
        "🚀 *Breed Accelerator* applied! Remaining breed time halved.", parse_mode="Markdown"
    )


async def _equip_title(update, tg_id: int, title_key: str):
    if title_key not in COSMETICS:
        await update.message.reply_text(
            "Unknown title. Use `/store` to see available titles.", parse_mode="Markdown"
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
