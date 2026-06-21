import random
import uuid
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db
from game.achievements import check_achievements
from game.species_data import ENCLOSURE_LEVELS
from utils import format_mention
from game.constants import LURE_MULTIPLIER, STAT_CAUGHT_MIN, STAT_CAUGHT_MAX

logger = logging.getLogger(__name__)


def wild_catch_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⚡ Claim it!", callback_data=f"wild_catch_{event_id}")]]
    )


async def wild_event_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    event_id = int(query.data.removeprefix("wild_catch_"))

    event = db.get_wild_event(event_id)
    if not event:
        await query.answer("This event no longer exists.", show_alert=True)
        return

    if event["caught_by_user_id"] is not None:
        await query.answer("Too slow — someone already caught it!", show_alert=True)
        return

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    species = db.get_species(event["species_id"])
    if not species:
        await query.answer("Something went wrong.", show_alert=True)
        return

    habitat = species["habitat"]
    enc_level = db.get_enclosure_level(tg_id, habitat)
    capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
    current = db.get_animal_count_by_habitat(tg_id, habitat)
    if current >= capacity:
        await query.answer(
            f"Your {habitat.title()} enclosure is full (Lv {enc_level}, capacity {capacity})!",
            show_alert=True,
        )
        return

    # Require a matching habitat lure
    lure_row = db.get_oldest_purchase(tg_id, f"lure_{habitat}")
    if not lure_row:
        await query.answer(
            f"You need a {habitat.title()} lure to catch this! Buy one from /store.",
            show_alert=True,
        )
        return

    db.consume_purchase(lure_row["id"])

    # Roll catch rate with lure multiplier — wild animals can still escape
    catch_rate = min(1.0, species["catch_rate"] * LURE_MULTIPLIER)
    if not random.random() < catch_rate:
        db.claim_wild_event(event_id, -1)
        await query.answer(
            f"🌿 {species['emoji']} {species['name']} got away!",
            show_alert=True,
        )
        try:
            await query.edit_message_text(
                f"🌿 *The wild {species['name']} got away!*",
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Failed to update wild event message %s", event_id)
        return

    claimed = db.claim_wild_event(event_id, tg_id)
    if not claimed:
        await query.answer("Too slow — someone already caught it!", show_alert=True)
        return

    animal_id = str(uuid.uuid4())
    db.add_animal(animal_id, tg_id, species["species_id"])
    shiny = random.random() < 0.015
    if shiny:
        db.set_animal_shiny(animal_id)
    db.set_animal_stats(
        animal_id,
        random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX),
        random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX),
        random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX),
    )
    shiny_str = "⭐ " if shiny else ""

    mention = format_mention(query.from_user.username, tg_id)
    await query.answer(
        f"🎉 You caught {species['emoji']} {shiny_str}{species['name']}!", show_alert=True
    )
    await check_achievements(tg_id, "wild_catch", ctx)
    await check_achievements(tg_id, "catch", ctx)
    try:
        await query.edit_message_text(
            f"⚡ *Wild event over!*\n"
            f"{species['emoji']} *{shiny_str}{species['name']}* was caught by *{mention}*!",
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("Failed to update wild event message %s", event_id)
