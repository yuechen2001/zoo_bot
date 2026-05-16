from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MOOD_EMOJIS = ["😢", "😐", "🙂", "😄", "🤩"]


def mood_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(e, callback_data=f"mood_{e}") for e in MOOD_EMOJIS]]
    )


def catch_keyboard(species_id: int, cost: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"🪙 {cost} coins", callback_data=f"catch_attempt_{species_id}"
                ),
                InlineKeyboardButton("❌ Skip", callback_data="catch_skip"),
            ]
        ]
    )


def breed_collect_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🥚 Collect offspring", callback_data="breed_collect"),
            ]
        ]
    )


def trade_keyboard(trade_id: int, recipient_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Accept", callback_data=f"trade_accept_{trade_id}_{recipient_id}"
                ),
                InlineKeyboardButton(
                    "❌ Decline", callback_data=f"trade_decline_{trade_id}_{recipient_id}"
                ),
            ]
        ]
    )
