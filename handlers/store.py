import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.store_data import STORE_ITEMS, CONSUMABLES, COSMETICS


def _store_text() -> str:
    lines = ["🏪 *Zoo Store*\n"]
    lines.append("*Consumables* (one-time use):")
    for key, item in CONSUMABLES.items():
        lines.append(
            f"  {item['emoji']} *{item['name']}* — {item['price']} 🪙\n    _{item['desc']}_"
        )
    lines.append("\n*Cosmetics* (titles shown in /zoo):")
    for key, item in COSMETICS.items():
        lines.append(
            f"  {item['emoji']} *{item['name']}* — {item['price']} 🪙\n    _{item['desc']}_"
        )
    lines.append(
        "\n*Commands:*\n"
        "`/store buy <item>` — purchase an item\n"
        "`/store use mega_feed <#>` — apply Mega Feed to animal #N\n"
        "`/store equip <title>` — set your active title\n\n"
        "Item keys: `mega_feed` `breed_boost` `lucky_token`\n"
        "`title_keeper` `title_whisperer` `title_legend`"
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
        await update.message.reply_text(_store_text(), parse_mode="Markdown")
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
                "Usage: `/store equip <title_key>`\n"
                "Keys: title\\_keeper, title\\_whisperer, title\\_legend",
                parse_mode="Markdown",
            )
            return
        await _equip_title(update, tg_id, args[1].lower())

    else:
        await update.message.reply_text(_store_text(), parse_mode="Markdown")


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

    category = item["category"]

    if category == "cosmetic":
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

    # Consumables
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
            await update.message.reply_text(
                "No active breed to boost! Refunded.",
            )
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
            "⚡ *Breed Boost* applied! Your breed time was cut by 2 hours.",
            parse_mode="Markdown",
        )

    elif item_key == "lucky_token":
        db.set_lucky_catch(tg_id, True)
        await update.message.reply_text(
            "🎯 *Lucky Token* activated! Your next /catch has 2× catch rate.",
            parse_mode="Markdown",
        )


async def _use_mega_feed(update, tg_id: int, position: int):
    purchase = None
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
            f"Unknown title `{title_key}`.\nAvailable: title\\_keeper, title\\_whisperer, title\\_legend",
            parse_mode="Markdown",
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
