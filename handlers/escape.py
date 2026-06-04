import datetime
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db
from game.constants import (
    ESCAPE_LURE_SUCCESS_RATE,
    ESCAPE_CHASE_SUCCESS_RATE,
    ESCAPE_RELEASE_REFUND_RATE,
)


def escape_keyboard(escape_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎣 Lure it back", callback_data=f"escape_{escape_id}_lure")],
            [InlineKeyboardButton("🏃 Chase it", callback_data=f"escape_{escape_id}_chase")],
            [InlineKeyboardButton("🕊️ Let it go", callback_data=f"escape_{escape_id}_release")],
        ]
    )


async def escape_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_", 2)  # ["escape", str(escape_id), action]
    escape_id = int(parts[1])
    action = parts[2]

    tg_id = query.from_user.id
    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    escape = db.get_escape(escape_id)
    if not escape:
        await query.answer("No such escape event.", show_alert=True)
        return

    if escape["user_id"] != tg_id:
        await query.answer("This isn't your animal!", show_alert=True)
        return

    if escape["resolved"] != 0:
        await query.answer("This escape event is already over.", show_alert=True)
        return

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    expires = datetime.datetime.fromisoformat(escape["expires_at"])
    if now > expires:
        await query.answer("Time's up — the window has closed!", show_alert=True)
        return

    animal = db.get_animal(escape["animal_id"])
    if not animal:
        await query.answer("The animal is already gone.", show_alert=True)
        db.resolve_escape(escape_id, 2)
        return

    name = animal["nickname"] or animal["species_name"]
    emoji = animal["emoji"]

    if action == "lure":
        lure_key = f"lure_{animal['habitat']}"
        purchase = db.get_oldest_purchase(tg_id, lure_key)
        if not purchase:
            await query.answer(
                f"You don't have a {animal['habitat']} lure! Try chasing instead.",
                show_alert=True,
            )
            return
        db.consume_purchase(purchase["id"])
        if random.random() < ESCAPE_LURE_SUCCESS_RATE:
            db.resolve_escape(escape_id, 1)
            await query.answer(f"🎣 The lure worked! {emoji} {name} is back!", show_alert=True)
            await query.edit_message_text(
                f"🎣 *Escape resolved!*\n\n{emoji} *{name}* was lured back safely!",
                parse_mode="Markdown",
            )
        else:
            db.delete_animal(escape["animal_id"])
            db.resolve_escape(escape_id, 2)
            await query.answer(
                f"🎣 The lure failed — {emoji} {name} got away for good!", show_alert=True
            )
            await query.edit_message_text(
                f"😢 *Escape failed!*\n\n{emoji} *{name}* wasn't tempted by the lure and disappeared.",
                parse_mode="Markdown",
            )

    elif action == "chase":
        if random.random() < ESCAPE_CHASE_SUCCESS_RATE:
            db.resolve_escape(escape_id, 1)
            await query.answer(f"🏃 You caught up to {emoji} {name}!", show_alert=True)
            await query.edit_message_text(
                f"🏃 *Escape resolved!*\n\nYou chased down {emoji} *{name}* and brought them back!",
                parse_mode="Markdown",
            )
        else:
            db.delete_animal(escape["animal_id"])
            db.resolve_escape(escape_id, 2)
            await query.answer(f"🏃 Couldn't catch up! {emoji} {name} got away!", show_alert=True)
            await query.edit_message_text(
                f"😢 *Escape failed!*\n\n{emoji} *{name}* was too fast and disappeared.",
                parse_mode="Markdown",
            )

    elif action == "release":
        refund = max(1, round(animal["catch_cost"] // 2 * ESCAPE_RELEASE_REFUND_RATE))
        db.add_coins(tg_id, refund)
        db.delete_animal(escape["animal_id"])
        db.resolve_escape(escape_id, 3)
        await query.answer(f"🕊️ You let {emoji} {name} go. +{refund} 🪙 refund.", show_alert=True)
        await query.edit_message_text(
            f"🕊️ *Released!*\n\n{emoji} *{name}* was set free. You got *{refund}* 🪙 back.",
            parse_mode="Markdown",
        )
