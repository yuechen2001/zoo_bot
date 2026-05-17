import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from keyboards import trade_keyboard
from config import TRADE_EXPIRY_MINUTES
from species_data import RARITY_LABELS, HABITATS, ENCLOSURE_LEVELS
from achievements import check_achievements


async def trade_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    proposer = db.get_user(tg_id)
    if not proposer:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    if len(args) != 3:
        await update.message.reply_text(
            "Usage: /trade @username <your position> <their position>\n"
            "Example: /trade @partner 2 3"
        )
        return

    raw_username, my_pos_str, their_pos_str = args
    if not my_pos_str.isdigit() or not their_pos_str.isdigit():
        await update.message.reply_text("Positions must be numbers. Example: /trade @partner 2 3")
        return

    my_pos = int(my_pos_str)
    their_pos = int(their_pos_str)
    username = raw_username.lstrip("@")

    recipient = db.get_user_by_username(username)
    if not recipient:
        await update.message.reply_text(f"@{username} hasn't started the bot yet.")
        return

    if recipient["user_id"] == tg_id:
        await update.message.reply_text("You can't trade with yourself!")
        return

    my_animal = db.get_animal_by_position(tg_id, my_pos)
    if not my_animal:
        await update.message.reply_text(f"You don't have an animal at position #{my_pos}.")
        return

    their_animal = db.get_animal_by_position(recipient["user_id"], their_pos)
    if not their_animal:
        await update.message.reply_text(
            f"@{username} doesn't have an animal at position #{their_pos}."
        )
        return

    if my_animal["is_breeding"]:
        name = my_animal["nickname"] or my_animal["species_name"]
        await update.message.reply_text(
            f"{my_animal['emoji']} {name} is currently breeding — can't trade!"
        )
        return

    if their_animal["is_breeding"]:
        name = their_animal["nickname"] or their_animal["species_name"]
        await update.message.reply_text(
            f"{their_animal['emoji']} {name} is currently breeding — can't trade!"
        )
        return

    if db.has_pending_trade_for_animal(my_animal["animal_id"]):
        await update.message.reply_text("That animal already has a pending trade. Cancel it first.")
        return

    if db.has_pending_trade_for_animal(their_animal["animal_id"]):
        name = their_animal["nickname"] or their_animal["species_name"]
        await update.message.reply_text(
            f"{their_animal['emoji']} {name} already has a pending trade."
        )
        return

    trade_id = db.create_trade(
        tg_id, recipient["user_id"], my_animal["animal_id"], their_animal["animal_id"]
    )

    my_name = my_animal["nickname"] or my_animal["species_name"]
    their_name = their_animal["nickname"] or their_animal["species_name"]
    my_rarity = RARITY_LABELS.get(my_animal["rarity"], my_animal["rarity"].title())
    their_rarity = RARITY_LABELS.get(their_animal["rarity"], their_animal["rarity"].title())
    proposer_name = update.effective_user.first_name

    await update.message.reply_text(
        f"🔄 *Trade Proposal*\n\n"
        f"*{proposer_name}* offers: {my_animal['emoji']} {my_name} ({my_rarity})\n"
        f"for @{username}'s: {their_animal['emoji']} {their_name} ({their_rarity})\n\n"
        f"_@{username}, you have {TRADE_EXPIRY_MINUTES} min to respond._",
        parse_mode="Markdown",
        reply_markup=trade_keyboard(trade_id, recipient["user_id"]),
    )


async def trade_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # format: trade_accept_{trade_id}_{recipient_id}  or  trade_decline_{...}
    parts = query.data.split("_")
    action = parts[1]  # "accept" or "decline"
    trade_id = int(parts[2])
    recipient_id = int(parts[3])

    if query.from_user.id != recipient_id:
        await query.answer("This isn't your trade!", show_alert=True)
        return

    trade = db.get_trade(trade_id)
    if not trade or trade["status"] != "pending":
        await query.answer("This trade is no longer active.")
        await query.edit_message_reply_markup(reply_markup=None)
        return

    created = datetime.datetime.fromisoformat(trade["created_at"])
    elapsed = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - created
    ).total_seconds() / 60
    if elapsed > TRADE_EXPIRY_MINUTES:
        db.resolve_trade(trade_id, "declined")
        await query.answer("Trade expired.")
        await query.edit_message_text("⏰ Trade expired — no response in time.")
        return

    proposer_animal = db.get_animal(trade["proposer_animal_id"])
    recipient_animal = db.get_animal(trade["recipient_animal_id"])

    p_name = proposer_animal["nickname"] or proposer_animal["species_name"]
    r_name = recipient_animal["nickname"] or recipient_animal["species_name"]

    if action == "accept":
        # Capacity check — only needed when animals are from different habitats
        p_habitat = proposer_animal["habitat"]
        r_habitat = recipient_animal["habitat"]
        proposer_id = trade["proposer_id"]

        if p_habitat != r_habitat:
            # Proposer gains recipient_animal (r_habitat) — check proposer's r_habitat
            used = db.get_animal_count_by_habitat(proposer_id, r_habitat)
            cap = ENCLOSURE_LEVELS[db.get_enclosure_level(proposer_id, r_habitat)]["capacity"]
            if used >= cap:
                h = HABITATS[r_habitat]
                await query.answer("Trade blocked — enclosure full!", show_alert=True)
                await query.edit_message_text(
                    f"❌ Trade cancelled — the proposer's {h['emoji']} *{h['name']}* enclosure is full.",
                    parse_mode="Markdown",
                )
                return

            # Recipient gains proposer_animal (p_habitat) — check recipient's p_habitat
            used = db.get_animal_count_by_habitat(recipient_id, p_habitat)
            cap = ENCLOSURE_LEVELS[db.get_enclosure_level(recipient_id, p_habitat)]["capacity"]
            if used >= cap:
                h = HABITATS[p_habitat]
                await query.answer("Trade blocked — enclosure full!", show_alert=True)
                await query.edit_message_text(
                    f"❌ Trade cancelled — your {h['emoji']} *{h['name']}* enclosure is full.",
                    parse_mode="Markdown",
                )
                return
        db.resolve_trade(trade_id, "accepted")
        await query.answer("Trade accepted! ✅")
        await query.edit_message_text(
            f"✅ *Trade complete!*\n\n"
            f"{proposer_animal['emoji']} {p_name} → @{query.from_user.username}\n"
            f"{recipient_animal['emoji']} {r_name} → other player\n\n"
            f"📋 Zoo positions have changed — use /zoo to see the new order.",
            parse_mode="Markdown",
        )
        trade = db.get_trade(trade_id)
        await check_achievements(query.from_user.id, "trade", ctx)
        await check_achievements(trade["proposer_id"], "trade", ctx)
    else:
        db.resolve_trade(trade_id, "declined")
        await query.answer("Trade declined.")
        await query.edit_message_text(
            f"❌ Trade declined.\n\n"
            f"{proposer_animal['emoji']} {p_name} stays put.\n"
            f"{recipient_animal['emoji']} {r_name} stays put."
        )
