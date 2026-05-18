import random
import uuid
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db
from achievements import check_achievements
from species_data import ENCLOSURE_LEVELS
from utils import format_mention

logger = logging.getLogger(__name__)

LURE_MULTIPLIER = 1.5


def wild_catch_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎣 Catch it!", callback_data=f"wild_catch_{event_id}")]]
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
        await query.answer("Use /start first to join!", show_alert=True)
        return

    with db.get_conn() as conn:
        species = conn.execute(
            "SELECT * FROM species WHERE species_id = ?", (event["species_id"],)
        ).fetchone()

    if not species:
        await query.answer("Something went wrong.", show_alert=True)
        return

    habitat = species["habitat"] or "woodland"
    enc_level = db.get_enclosure_level(tg_id, habitat)
    capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
    current = db.get_animal_count_by_habitat(tg_id, habitat)
    if current >= capacity:
        await query.answer(
            f"Your {habitat} enclosure is full (Lv {enc_level}, capacity {capacity})!",
            show_alert=True,
        )
        return

    # Require a matching habitat lure
    with db.get_conn() as conn:
        lure_row = conn.execute(
            "SELECT id FROM user_purchases WHERE user_id = ? AND item_key = ? "
            "ORDER BY purchased_at ASC LIMIT 1",
            (tg_id, f"lure_{habitat}"),
        ).fetchone()

    if not lure_row:
        await query.answer(
            f"You need a {habitat} lure to catch this! Buy one from /store.",
            show_alert=True,
        )
        return

    with db.get_conn() as conn:
        conn.execute("DELETE FROM user_purchases WHERE id = ?", (lure_row["id"],))

    # Roll catch rate with lure multiplier — wild animals can still escape
    catch_rate = min(1.0, species["catch_rate"] * LURE_MULTIPLIER)
    if not random.random() < catch_rate:
        await query.answer(
            f"🌿 {species['emoji']} {species['name']} got away! Someone else might still catch it.",
            show_alert=True,
        )
        return

    claimed = db.claim_wild_event(event_id, tg_id)
    if not claimed:
        await query.answer("Too slow — someone already caught it!", show_alert=True)
        return

    animal_id = str(uuid.uuid4())
    db.add_animal(animal_id, tg_id, species["species_id"])

    mention = format_mention(query.from_user.username, tg_id)
    await query.answer(f"🎉 You caught {species['emoji']} {species['name']}!", show_alert=True)
    await check_achievements(tg_id, "wild_catch", ctx)
    try:
        await query.edit_message_text(
            f"🌿 *Wild event over!*\n"
            f"{species['emoji']} *{species['name']}* was caught by *{mention}*!",
            parse_mode="Markdown",
        )
    except Exception:
        pass
