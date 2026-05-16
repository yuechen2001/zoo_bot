from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MOOD_EMOJIS = ["😢", "😐", "🙂", "😄", "🤩"]


def mood_keyboard(tg_id: int):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(e, callback_data=f"mood_{tg_id}_{e}") for e in MOOD_EMOJIS]]
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
