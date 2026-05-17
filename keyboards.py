from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from species_data import HABITATS

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


def enclosure_upgrade_keyboard(habitats_with_cost: list[tuple[str, int]]):
    """habitats_with_cost: list of (habitat_key, upgrade_cost) for enclosures not at max level."""
    buttons = [
        [InlineKeyboardButton(f"⬆️ {habitat} ({cost} 🪙)", callback_data=f"enc_upgrade_{habitat}")]
        for habitat, cost in habitats_with_cost
    ]
    return InlineKeyboardMarkup(buttons)


def zoo_page_keyboard(owner_id: int, page: int, habitat_keys: list[str]) -> InlineKeyboardMarkup:
    buttons = []
    if page > 0:
        prev_emoji = HABITATS[habitat_keys[page - 1]]["emoji"]
        buttons.append(
            InlineKeyboardButton(f"◀ {prev_emoji}", callback_data=f"zoo_page_{owner_id}_{page - 1}")
        )
    buttons.append(
        InlineKeyboardButton(f"{page + 1} / {len(habitat_keys)}", callback_data="zoo_noop")
    )
    if page < len(habitat_keys) - 1:
        next_emoji = HABITATS[habitat_keys[page + 1]]["emoji"]
        buttons.append(
            InlineKeyboardButton(f"{next_emoji} ▶", callback_data=f"zoo_page_{owner_id}_{page + 1}")
        )
    return InlineKeyboardMarkup([buttons])


def store_keyboard(owned_keys: set) -> InlineKeyboardMarkup:
    from game.store_data import CONSUMABLES, COSMETICS

    consumable_row = [
        InlineKeyboardButton(
            f"{item['emoji']} {item['price']} 🪙",
            callback_data=f"store_buy_{key}",
        )
        for key, item in CONSUMABLES.items()
    ]
    cosmetic_row = [
        InlineKeyboardButton(
            (
                f"✅ {item['emoji']} Equip"
                if key in owned_keys
                else f"{item['emoji']} {item['price']} 🪙"
            ),
            callback_data=f"store_equip_{key}" if key in owned_keys else f"store_buy_{key}",
        )
        for key, item in COSMETICS.items()
    ]
    return InlineKeyboardMarkup([consumable_row, cosmetic_row])


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
