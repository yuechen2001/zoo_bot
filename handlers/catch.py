import uuid
import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.catch_engine import roll_encounter, pick_species, roll_catch
from keyboards import catch_keyboard
from species_data import RARITY_LABELS
from config import CATCH_EXPIRY_MINUTES


async def catch_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    with db.get_conn() as conn:
        rarity = roll_encounter()
        species = pick_species(rarity, conn)

    if not species:
        await update.message.reply_text("No animals found... try again!")
        return

    # Store the pending catch in context so callback can verify it hasn't expired
    ctx.user_data["pending_catch"] = {
        "species_id": species["species_id"],
        "catch_rate": species["catch_rate"],
        "catch_cost": species["catch_cost"],
        "rarity": species["rarity"],
        "name": species["name"],
        "emoji": species["emoji"],
        "at": datetime.datetime.utcnow().isoformat(),
    }

    rarity_label = RARITY_LABELS.get(rarity, rarity.title())
    await update.message.reply_text(
        f"🌿 A wild *{species['emoji']} {species['name']}* appeared!\n"
        f"{rarity_label}\n\n"
        f"Catch rate: {int(species['catch_rate'] * 100)}%\n"
        f"Your coins: *{user['coins']}* 🪙\n\n"
        f"_Skip costs {species['catch_cost'] // 2} coins. You have {CATCH_EXPIRY_MINUTES} min._",
        parse_mode="Markdown",
        reply_markup=catch_keyboard(species["species_id"], species["catch_cost"]),
    )


async def catch_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    data = query.data

    if data == "catch_skip":
        pending = ctx.user_data.pop("pending_catch", None)
        skip_cost = (pending["catch_cost"] // 2) if pending else 0
        if skip_cost:
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE users SET coins = MAX(0, coins - ?) WHERE user_id = ?",
                    (skip_cost, tg_id),
                )
        await query.answer(f"-{skip_cost} coins for skipping")
        await query.edit_message_text(
            f"You let it go. 🌿\n_{skip_cost} coins lost._",
            parse_mode="Markdown",
        )
        return

    # catch_attempt_<species_id>
    pending = ctx.user_data.get("pending_catch")
    if not pending:
        await query.answer("No active catch — use /catch to find one.")
        return

    # Check expiry
    at = datetime.datetime.fromisoformat(pending["at"])
    if (datetime.datetime.utcnow() - at).total_seconds() > CATCH_EXPIRY_MINUTES * 60:
        await query.answer("Too slow! The animal escaped.")
        await query.edit_message_text("⏰ Time's up — it got away. Try /catch again!")
        ctx.user_data.pop("pending_catch", None)
        return

    user = db.get_user(tg_id)
    cost = pending["catch_cost"]

    if user["coins"] < cost:
        await query.answer(f"Not enough coins! Need {cost}.")
        return

    # Deduct coins regardless of outcome
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = coins - ? WHERE user_id = ?",
            (cost, tg_id),
        )

    success = roll_catch(pending["catch_rate"])
    ctx.user_data.pop("pending_catch", None)

    if success:
        animal_id = str(uuid.uuid4())
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO animals (animal_id, user_id, species_id) VALUES (?, ?, ?)",
                (animal_id, tg_id, pending["species_id"]),
            )
        await query.answer("Caught!")
        await query.edit_message_text(
            f"🎉 You caught the {pending['emoji']} *{pending['name']}*!\n\n"
            f"Use `/name <number> <name>` to give it a nickname.",
            parse_mode="Markdown",
        )
    else:
        await query.answer("It escaped...")
        await query.edit_message_text(
            f"💨 The {pending['emoji']} *{pending['name']}* broke free and ran away!\n"
            f"_{cost} coins spent, no refund._",
            parse_mode="Markdown",
        )
