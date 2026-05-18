import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from achievements import check_achievements
from game.store_data import STORE_ITEMS, CONSUMABLES, COSMETICS
from keyboards import store_keyboard


def _store_text() -> str:
    lines = ["🏪 *Zoo Store*\n"]
    lines.append("*Consumables* (one-time use):")
    for key, item in CONSUMABLES.items():
        lines.append(f"  {item['emoji']} *{item['name']}* — {item['price']} 🪙\n  {item['desc']}")
    lines.append("\n*Titles* (shown in your /zoo):")
    for key, item in COSMETICS.items():
        lines.append(f"  {item['emoji']} *{item['name']}* — {item['price']} 🪙\n  {item['desc']}")
    lines.append(
        "\n_Tap a button to buy. After buying Mega Feed use_ `/store use mega_feed <#>`_._"
    )
    return "\n".join(lines)


def _owned_cosmetic_keys(tg_id: int) -> set:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT item_key FROM user_purchases WHERE user_id = ? AND item_key LIKE 'title_%'",
            (tg_id,),
        ).fetchall()
    return {r["item_key"] for r in rows}


async def store_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if not args:
        owned = _owned_cosmetic_keys(tg_id)
        await update.message.reply_text(
            _store_text(), parse_mode="Markdown", reply_markup=store_keyboard(owned)
        )
        return

    sub = args[0].lower()

    if sub == "buy":
        if len(args) < 2:
            await update.message.reply_text("Usage: `/store buy <item_key>`", parse_mode="Markdown")
            return
        await _buy(update, tg_id, user, args[1].lower())

    elif sub == "use":
        if len(args) < 3 or args[1].lower() != "mega_feed" or not args[2].isdigit():
            await update.message.reply_text(
                "Usage: `/store use mega_feed <animal number>`", parse_mode="Markdown"
            )
            return
        await _use_mega_feed(update, tg_id, int(args[2]))

    elif sub == "equip":
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: `/store equip <title_key>`", parse_mode="Markdown"
            )
            return
        await _equip_title(update, tg_id, args[1].lower())

    else:
        owned = _owned_cosmetic_keys(tg_id)
        await update.message.reply_text(
            _store_text(), parse_mode="Markdown", reply_markup=store_keyboard(owned)
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
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE users SET coins = coins - ? WHERE user_id = ?", (item["price"], tg_id)
            )
        db.record_purchase(tg_id, key)
        owned = _owned_cosmetic_keys(tg_id)
        await query.answer(f"✅ Purchased {item['emoji']} {item['name']}! Tap Equip to wear it.")
        try:
            await query.edit_message_reply_markup(reply_markup=store_keyboard(owned))
        except Exception:
            pass
        return

    # Consumables
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (item["price"], tg_id))

    if key == "mega_feed":
        db.record_purchase(tg_id, key)
        await query.answer(
            "✅ Mega Feed purchased! Use /store use mega_feed <animal #> to apply it.",
            show_alert=True,
        )

    elif key == "breed_boost":
        pending = db.get_pending_breed(tg_id)
        if not pending:
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE users SET coins = coins + ? WHERE user_id = ?", (item["price"], tg_id)
                )
            await query.answer("No active breed to boost! Refunded.", show_alert=True)
            return
        new_ready_at = (
            datetime.datetime.fromisoformat(pending["ready_at"]) - datetime.timedelta(hours=2)
        ).isoformat()
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE breeding_queue SET ready_at = ? WHERE id = ?",
                (new_ready_at, pending["id"]),
            )
        await query.answer("⚡ Breed Boost applied! Breed time cut by 2 hours.", show_alert=True)

    elif key == "lucky_token":
        db.set_lucky_catch(tg_id, True)
        await query.answer(
            "🎯 Lucky Token activated! Next /catch has 2× catch rate.", show_alert=True
        )

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
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE users SET coins = coins - ? WHERE user_id = ?", (item["price"], tg_id)
            )
        db.record_purchase(tg_id, item_key)
        await update.message.reply_text(
            f"✅ Purchased {item['emoji']} *{item['name']}*!\n"
            f"Use `/store equip {item_key}` to display it in your zoo.",
            parse_mode="Markdown",
        )
        return

    with db.get_conn() as conn:
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (item["price"], tg_id))

    if item_key == "mega_feed":
        db.record_purchase(tg_id, item_key)
        await update.message.reply_text(
            f"✅ Purchased {item['emoji']} *Mega Feed*!\n"
            f"Use `/store use mega_feed <animal #>` to apply it.",
            parse_mode="Markdown",
        )
    elif item_key == "breed_boost":
        pending = db.get_pending_breed(tg_id)
        if not pending:
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE users SET coins = coins + ? WHERE user_id = ?", (item["price"], tg_id)
                )
            await update.message.reply_text("No active breed to boost! Refunded.")
            return
        new_ready_at = (
            datetime.datetime.fromisoformat(pending["ready_at"]) - datetime.timedelta(hours=2)
        ).isoformat()
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE breeding_queue SET ready_at = ? WHERE id = ?",
                (new_ready_at, pending["id"]),
            )
        await update.message.reply_text(
            "⚡ *Breed Boost* applied! Your breed time was cut by 2 hours.", parse_mode="Markdown"
        )
    elif item_key == "lucky_token":
        db.set_lucky_catch(tg_id, True)
        await update.message.reply_text(
            "🎯 *Lucky Token* activated! Your next /catch has 2× catch rate.", parse_mode="Markdown"
        )


async def _use_mega_feed(update, tg_id: int, position: int):
    with db.get_conn() as conn:
        purchase = conn.execute(
            "SELECT id FROM user_purchases WHERE user_id = ? AND item_key = 'mega_feed' "
            "ORDER BY purchased_at ASC LIMIT 1",
            (tg_id,),
        ).fetchone()

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

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE animals SET hunger = 100, hunger_alerted = NULL WHERE animal_id = ?",
            (animal["animal_id"],),
        )
        conn.execute("DELETE FROM user_purchases WHERE id = ?", (purchase["id"],))

    name = animal["nickname"] or animal["species_name"]
    await update.message.reply_text(
        f"🍖 *Mega Feed* applied! {animal['emoji']} *{name}* hunger restored to 100.",
        parse_mode="Markdown",
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
