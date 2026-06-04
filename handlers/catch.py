import asyncio
import random
import uuid
import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.catch_engine import roll_encounter, roll_catch
from keyboards import catch_keyboard, lure_keyboard, no_lure_keyboard
from game.species_data import RARITY_LABELS, HABITATS, ENCLOSURE_LEVELS
from config import CATCH_EXPIRY_MINUTES
from game.achievements import check_achievements
from game.constants import LURE_MULTIPLIER, NO_LURE_COST


async def catch_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    counts = db.get_item_counts(tg_id)
    from game.store_data import LURES

    has_lures = any(counts.get(k, 0) > 0 for k in LURES)

    ctx.user_data.pop("pending_catch", None)

    catch_chat_id, catch_message_id = db.get_catch_message(tg_id)
    old_cmd = ctx.user_data.pop("catch_cmd", None)

    if has_lures:
        lure_text = "🎣 *Choose a lure!*\n_Habitat lures give 1.5× catch rate._"
        lure_kb = lure_keyboard(counts)
    else:
        lure_text = f"🌿 *Go catch an animal!*\n_No lure — costs {NO_LURE_COST} 🪙, a random animal will appear._"
        lure_kb = no_lure_keyboard()

    msg = await update.message.reply_text(lure_text, parse_mode="Markdown", reply_markup=lure_kb)
    db.set_catch_message(tg_id, update.effective_chat.id, msg.message_id)
    ctx.user_data["catch_cmd"] = (update.effective_chat.id, update.message.message_id)

    if catch_chat_id and catch_message_id:
        asyncio.create_task(
            ctx.bot.delete_message(chat_id=catch_chat_id, message_id=catch_message_id)
        )
    if old_cmd:
        asyncio.create_task(ctx.bot.delete_message(chat_id=old_cmd[0], message_id=old_cmd[1]))


async def catch_lure_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    habitat = query.data.removeprefix("catch_lure_")

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    is_no_lure = habitat == "none"
    is_habitat_lure = not is_no_lure

    lure_multiplier = LURE_MULTIPLIER if is_habitat_lure else 1.0
    enc_catch_bonus = 0.0

    if is_no_lure:
        if user["coins"] < NO_LURE_COST:
            await query.answer(f"Need {NO_LURE_COST} 🪙 to search without a lure!", show_alert=True)
            return
        db.add_coins(tg_id, -NO_LURE_COST)
    else:
        # Verify lure is still in inventory (race condition guard)
        purchase = db.get_oldest_purchase(tg_id, f"lure_{habitat}")
        if not purchase:
            await query.answer("You don't have that lure anymore!", show_alert=True)
            return
        # Pre-check enclosure capacity before consuming
        enc_level = db.get_enclosure_level(tg_id, habitat)
        capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
        enc_catch_bonus = ENCLOSURE_LEVELS[enc_level]["catch_rate_bonus"]
        used = db.get_animal_count_by_habitat(tg_id, habitat)
        if used >= capacity:
            h = HABITATS[habitat]
            await query.answer(
                f"Your {h['emoji']} {h['name']} enclosure is full — lure not consumed.",
                show_alert=True,
            )
            return
    is_unfiltered = is_no_lure

    rarity = roll_encounter()
    if user["catch_net_active"]:
        rarity = "legendary"
    elif habitat == "mythic":
        rarity = random.choices(["epic", "legendary"], weights=[30, 10])[0]
    elif user["epic_magnet_active"] and rarity in ("common", "rare"):
        epic_candidates = db.get_species_candidates("epic", None if is_unfiltered else habitat)
        if epic_candidates:
            rarity = "epic"
        db.set_epic_magnet(tg_id, False)
    elif user["rare_magnet_active"] and rarity == "common":
        rare_candidates = db.get_species_candidates("rare", None if is_unfiltered else habitat)
        if rare_candidates:
            rarity = "rare"
        db.set_rare_magnet(
            tg_id, False
        )  # one-shot: consumed on the next common roll even if no rare candidates exist
    candidates = db.get_species_candidates(rarity, None if is_unfiltered else habitat)
    species = random.choice(candidates) if candidates else None

    if not species:
        await query.answer("No animals found — try again!", show_alert=True)
        return

    if is_habitat_lure:
        db.consume_purchase(purchase["id"])

    h = HABITATS[species["habitat"]] if is_unfiltered else HABITATS[habitat]
    catch_rate_display = (
        "100% 🪤"
        if user["catch_net_active"]
        else f"{min(100, int((species['catch_rate'] * lure_multiplier + enc_catch_bonus) * 100))}%"
    )

    msg = await query.edit_message_text(
        f"🌿 A wild *{species['emoji']} {species['name']}* appeared!\n"
        f"{RARITY_LABELS.get(rarity, rarity.title())} | {h['emoji']} {h['name']}\n\n"
        f"Catch rate: {catch_rate_display}\n\n"
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
        "lure_multiplier": lure_multiplier,
        "enc_catch_bonus": enc_catch_bonus,
    }


async def catch_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    data = query.data

    if data == "catch_cancel":
        ctx.user_data.pop("pending_catch", None)
        await query.answer("Cancelled")
        await query.edit_message_text("🎣 Search cancelled.")
        return

    if data == "catch_skip":
        ctx.user_data.pop("pending_catch", None)
        await query.answer("Skipped")
        await query.edit_message_text("You let it go. 🌿")
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

    db.add_coins(tg_id, -cost)

    catch_rate = pending["catch_rate"] * pending.get("lure_multiplier", 1.0)
    catch_rate += pending.get("enc_catch_bonus", 0.0)
    catch_rate = min(1.0, catch_rate)
    if user["lucky_catch_active"]:
        catch_rate = min(1.0, catch_rate * 2)
        db.set_lucky_catch(tg_id, False)
    if user["catch_net_active"]:
        catch_rate = 1.0
        db.set_catch_net(tg_id, False)

    success = roll_catch(catch_rate)
    ctx.user_data.pop("pending_catch", None)

    if success:
        animal_id = str(uuid.uuid4())
        db.add_animal(animal_id, tg_id, pending["species_id"])
        shiny = random.random() < 0.015
        if shiny:
            db.set_animal_shiny(animal_id)
        shiny_str = "⭐ " if shiny else ""
        await query.answer("Caught!")
        await query.edit_message_text(
            f"🎉 You caught the {pending['emoji']} *{shiny_str}{pending['name']}*!\n\n"
            f"Use /name to give it a nickname.",
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
