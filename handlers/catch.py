import uuid
import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.catch_engine import roll_encounter, pick_species, roll_catch
from keyboards import catch_keyboard
from species_data import RARITY_LABELS, HABITATS, ENCLOSURE_LEVELS
from config import CATCH_EXPIRY_MINUTES
from achievements import check_achievements

ENCOUNTER_FEE = 10


async def catch_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    if user["coins"] < ENCOUNTER_FEE:
        await update.message.reply_text(f"Not enough coins! Searching costs {ENCOUNTER_FEE} 🪙.")
        return

    with db.get_conn() as conn:
        rarity = roll_encounter()
        species = pick_species(rarity, conn)

    if not species:
        await update.message.reply_text("No animals found... try again!")
        return

    # Check capacity before charging anything
    habitat = db.get_species_habitat(species["species_id"])
    used = db.get_animal_count_by_habitat(tg_id, habitat)
    enc_level = db.get_enclosure_level(tg_id, habitat)
    capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
    if used >= capacity:
        h = HABITATS[habitat]
        await update.message.reply_text(
            f"Your {h['emoji']} *{h['name']}* enclosure is full! (Lv {enc_level}, {used}/{capacity})\n\n"
            f"/sell an animal or use /enclosures to upgrade.",
            parse_mode="Markdown",
        )
        return

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = coins - ? WHERE user_id = ?",
            (ENCOUNTER_FEE, tg_id),
        )
    user = db.get_user(tg_id)

    # Invalidate any previous encounter so its "Attempt" button can't catch the new species
    old = ctx.user_data.get("pending_catch")
    if old and old.get("message_id"):
        try:
            await ctx.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=old["message_id"],
                text="🌿 The previous encounter fled — you started a new search.",
            )
        except Exception:
            pass

    msg = await update.message.reply_text(
        f"🌿 A wild *{species['emoji']} {species['name']}* appeared!\n"
        f"{RARITY_LABELS.get(rarity, rarity.title())}\n\n"
        f"Catch rate: {int(species['catch_rate'] * 100)}%\n"
        f"Your coins: *{user['coins']}* 🪙\n\n"
        f"_You have {CATCH_EXPIRY_MINUTES} min to decide._",
        parse_mode="Markdown",
        reply_markup=catch_keyboard(species["species_id"], species["catch_cost"]),
    )

    ctx.user_data["pending_catch"] = {
        "species_id": species["species_id"],
        "catch_rate": species["catch_rate"],
        "catch_cost": species["catch_cost"],
        "rarity": species["rarity"],
        "name": species["name"],
        "emoji": species["emoji"],
        "at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(),
        "message_id": msg.message_id,
    }


async def catch_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    data = query.data

    if data == "catch_skip":
        ctx.user_data.pop("pending_catch", None)
        await query.answer("Skipped")
        await query.edit_message_text("You let it go. 🌿", parse_mode="Markdown")
        return

    # catch_attempt_<species_id>
    _, __, species_id_str = data.partition("catch_attempt_")
    pending = ctx.user_data.get("pending_catch")
    if not pending:
        await query.answer("No active catch — use /catch to find one.")
        return

    # Guard against clicking an old message after a new /catch was issued
    if str(pending["species_id"]) != species_id_str:
        await query.answer(
            "This encounter is outdated — use /catch for a fresh one.", show_alert=True
        )
        return

    # Check expiry
    at = datetime.datetime.fromisoformat(pending["at"])
    if (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - at
    ).total_seconds() > CATCH_EXPIRY_MINUTES * 60:
        await query.answer("Too slow! The animal escaped.")
        await query.edit_message_text("⏰ Time's up — it got away. Try /catch again!")
        ctx.user_data.pop("pending_catch", None)
        return

    user = db.get_user(tg_id)
    cost = pending["catch_cost"]

    if user["coins"] < cost:
        await query.answer(f"Not enough coins! Need {cost}.")
        return

    # Re-check capacity before charging — it may have filled up since the offer
    habitat = db.get_species_habitat(pending["species_id"])
    used = db.get_animal_count_by_habitat(tg_id, habitat)
    enc_level = db.get_enclosure_level(tg_id, habitat)
    capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
    if used >= capacity:
        h = HABITATS[habitat]
        await query.answer("Enclosure full!", show_alert=True)
        await query.edit_message_text(
            f"Your {h['emoji']} *{h['name']}* enclosure is full! (Lv {enc_level}, {used}/{capacity})\n\n"
            f"/sell an animal or use /enclosures to upgrade.",
            parse_mode="Markdown",
        )
        ctx.user_data.pop("pending_catch", None)
        return

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
        await check_achievements(tg_id, "catch", ctx)
    else:
        await query.answer("It escaped...")
        await query.edit_message_text(
            f"💨 The {pending['emoji']} *{pending['name']}* broke free and ran away!\n"
            f"_{cost} coins spent, no refund._",
            parse_mode="Markdown",
        )
