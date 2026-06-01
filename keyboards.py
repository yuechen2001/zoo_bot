from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from game.species_data import HABITATS
from game.constants import MIN_INVEST, SPIN_COST, MAX_BET, ANIMAL_PAGE_SIZE

MOOD_EMOJIS = ["😢", "😐", "🙂", "😄", "🤩"]

RARITY_SQUARE = {
    "common": "⬜",
    "uncommon": "🟩",
    "rare": "🟦",
    "epic": "🟪",
    "legendary": "🟨",
}

_INVEST_PRESETS = [50, 100, 250, 500]


def animal_picker_keyboard(
    animals: list,
    callback_prefix: str,
    cancel_callback: str,
    disabled_ids: set = None,
    page: int = 0,
    page_callback_prefix: str = None,
) -> InlineKeyboardMarkup:
    disabled_ids = disabled_ids or set()
    total = len(animals)
    total_pages = max(1, (total + ANIMAL_PAGE_SIZE - 1) // ANIMAL_PAGE_SIZE)
    start = page * ANIMAL_PAGE_SIZE
    page_animals = animals[start : start + ANIMAL_PAGE_SIZE]

    rows = []
    for i, animal in enumerate(page_animals):
        pos = start + i + 1  # global 1-based position
        aid = animal["animal_id"]
        square = RARITY_SQUARE.get(animal["rarity"], "⬜")
        label_name = animal["nickname"] or animal["species_name"]
        if aid in disabled_ids or animal["is_breeding"]:
            label = f"🔒 {animal['emoji']} #{pos} {label_name}"
            rows.append([InlineKeyboardButton(label, callback_data="zoo_noop")])
        else:
            label = f"{square} {animal['emoji']} #{pos} {label_name}"
            rows.append([InlineKeyboardButton(label, callback_data=f"{callback_prefix}_{pos}")])

    if page_callback_prefix and total_pages > 1:
        nav = []
        if page > 0:
            nav.append(
                InlineKeyboardButton("⬅️", callback_data=f"{page_callback_prefix}_{page - 1}")
            )
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="zoo_noop"))
        if page < total_pages - 1:
            nav.append(
                InlineKeyboardButton("➡️", callback_data=f"{page_callback_prefix}_{page + 1}")
            )
        rows.append(nav)

    rows.append([InlineKeyboardButton("❌ Cancel", callback_data=cancel_callback)])
    return InlineKeyboardMarkup(rows)


def invest_keyboard(user_coins: int, has_active: bool, is_ready: bool) -> InlineKeyboardMarkup:
    if has_active:
        if is_ready:
            return InlineKeyboardMarkup(
                [[InlineKeyboardButton("🪙 Collect now", callback_data="invest_collect")]]
            )
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("⏳ Waiting…", callback_data="zoo_noop")]]
        )
    preset_row = [
        InlineKeyboardButton(
            f"{amt} 🪙" if user_coins >= amt else f"💸 {amt}",
            callback_data=f"invest_deposit_{amt}" if user_coins >= amt else "zoo_noop",
        )
        for amt in _INVEST_PRESETS
    ]
    rows = [preset_row[:2], preset_row[2:]]
    if user_coins >= MIN_INVEST:
        rows.append(
            [InlineKeyboardButton(f"💰 All in ({user_coins} 🪙)", callback_data="invest_max")]
        )
    else:
        rows.append(
            [InlineKeyboardButton(f"💸 Need {MIN_INVEST} 🪙 min", callback_data="zoo_noop")]
        )
    return InlineKeyboardMarkup(rows)


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


def store_welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🧪 Items", callback_data="store_tab_items"),
                InlineKeyboardButton("🎣 Lures", callback_data="store_tab_lures"),
                InlineKeyboardButton("🎩 Titles", callback_data="store_tab_titles"),
            ]
        ]
    )


def store_tab_keyboard(section: str, owned_keys: set, counts: dict) -> InlineKeyboardMarkup:
    from game.store_data import ITEMS, LURES, COSMETICS

    tab_defs = [("items", "🧪 Items"), ("lures", "🎣 Lures"), ("titles", "🎩 Titles")]
    tab_row = []
    for key, label in tab_defs:
        if key == section:
            tab_row.append(InlineKeyboardButton(f"▸ {label} ◂", callback_data="zoo_noop"))
        else:
            tab_row.append(InlineKeyboardButton(label, callback_data=f"store_tab_{key}"))

    rows = [tab_row]

    if section == "items":
        btns = [
            InlineKeyboardButton(
                f"{item['emoji']} {item['price']} 🪙",
                callback_data=f"store_buy_{key}",
            )
            for key, item in ITEMS.items()
        ]
    elif section == "lures":
        btns = [
            InlineKeyboardButton(
                f"{item['emoji']} {item['price']} 🪙",
                callback_data=f"store_buy_{key}",
            )
            for key, item in LURES.items()
        ]
    else:
        btns = [
            InlineKeyboardButton(
                (
                    f"✅ {item['emoji']}"
                    if key in owned_keys
                    else f"{item['emoji']} {item['price']} 🪙"
                ),
                callback_data="zoo_noop" if key in owned_keys else f"store_buy_{key}",
            )
            for key, item in COSMETICS.items()
        ]

    for i in range(0, len(btns), 3):
        rows.append(btns[i : i + 3])

    return InlineKeyboardMarkup(rows)


def help_keyboard(current_section: str) -> InlineKeyboardMarkup:
    sections = [
        ("zoo", "🦁 Zoo"),
        ("breeding", "🥚 Breeding"),
        ("store", "🏪 Store"),
        ("coins", "🪙 Coins"),
        ("more", "📋 More"),
    ]
    row1 = []
    row2 = []
    for i, (key, label) in enumerate(sections):
        btn = (
            InlineKeyboardButton(f"▸ {label} ◂", callback_data="zoo_noop")
            if key == current_section
            else InlineKeyboardButton(label, callback_data=f"help_tab_{key}")
        )
        (row1 if i < 3 else row2).append(btn)
    return InlineKeyboardMarkup([row1, row2])


def achievements_keyboard(user_id: int, current_filter: str) -> InlineKeyboardMarkup:
    tabs = [("earned", "🏆 Earned"), ("all", "All"), ("locked", "🔒 Locked")]
    row = []
    for key, label in tabs:
        if key == current_filter:
            row.append(InlineKeyboardButton(f"▸ {label} ◂", callback_data="zoo_noop"))
        else:
            row.append(InlineKeyboardButton(label, callback_data=f"ach_tab_{user_id}_{key}"))
    return InlineKeyboardMarkup([row])


def directory_page_keyboard(user_id: int, page: int, habitat_keys: list) -> InlineKeyboardMarkup:
    buttons = []
    for idx, key in enumerate(habitat_keys):
        h = HABITATS[key]
        label = f"{h['emoji']} {h['name']}"
        if idx == page:
            buttons.append(InlineKeyboardButton(f"▸ {label} ◂", callback_data="zoo_noop"))
        else:
            buttons.append(InlineKeyboardButton(label, callback_data=f"dir_page_{user_id}_{idx}"))
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)


def breed_collect_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🥚 Collect offspring", callback_data="breed_collect"),
            ]
        ]
    )


def enclosure_upgrade_keyboard(
    habitats_with_cost: list[tuple[str, int]],
    tg_id: int,
    page: int = 0,
    total_pages: int = 1,
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                f"⬆️ {habitat} ({cost} 🪙)", callback_data=f"enc_upgrade_{tg_id}_{habitat}"
            )
        ]
        for habitat, cost in habitats_with_cost
    ]
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"enc_page_{tg_id}_{page - 1}"))
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="zoo_noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"enc_page_{tg_id}_{page + 1}"))
        buttons.append(nav)
    buttons.append(
        [InlineKeyboardButton("💰 Collect income", callback_data=f"enc_collect_{tg_id}")]
    )
    return InlineKeyboardMarkup(buttons)


def zoo_page_keyboard(owner_id: int, page: int, habitat_keys: list[str]) -> InlineKeyboardMarkup:
    buttons = []
    for idx, key in enumerate(habitat_keys):
        h = HABITATS[key]
        label = f"{h['emoji']} {h['name']}"
        if idx == page:
            buttons.append(InlineKeyboardButton(f"▸ {label} ◂", callback_data="zoo_noop"))
        else:
            buttons.append(InlineKeyboardButton(label, callback_data=f"zoo_page_{owner_id}_{idx}"))
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)


def store_keyboard(owned_keys: set) -> InlineKeyboardMarkup:
    from game.store_data import ITEMS, LURES, COSMETICS

    rows = []

    item_buttons = [
        InlineKeyboardButton(
            f"{item['emoji']} {item['price']} 🪙",
            callback_data=f"store_buy_{key}",
        )
        for key, item in ITEMS.items()
    ]
    for i in range(0, len(item_buttons), 3):
        rows.append(item_buttons[i : i + 3])

    lure_buttons = [
        InlineKeyboardButton(
            f"{item['emoji']} {item['price']} 🪙",
            callback_data=f"store_buy_{key}",
        )
        for key, item in LURES.items()
    ]
    for i in range(0, len(lure_buttons), 3):
        rows.append(lure_buttons[i : i + 3])

    cosmetic_row = [
        InlineKeyboardButton(
            f"✅ {item['emoji']}" if key in owned_keys else f"{item['emoji']} {item['price']} 🪙",
            callback_data="zoo_noop" if key in owned_keys else f"store_buy_{key}",
        )
        for key, item in COSMETICS.items()
    ]
    rows.append(cosmetic_row)
    return InlineKeyboardMarkup(rows)


def no_lure_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎲 Catch!", callback_data="catch_lure_none")]]
    )


def lure_keyboard(lure_counts: dict[str, int]) -> InlineKeyboardMarkup:
    from game.store_data import LURES

    available = [
        (key, item, lure_counts.get(key, 0))
        for key, item in LURES.items()
        if lure_counts.get(key, 0) > 0
    ]
    rows = []
    for i in range(0, len(available), 3):
        chunk = available[i : i + 3]
        rows.append(
            [
                InlineKeyboardButton(
                    f"{item['emoji']} {HABITATS[key.removeprefix('lure_')]['name']}"
                    + (f" ×{n}" if n > 1 else ""),
                    callback_data=f"catch_lure_{key.removeprefix('lure_')}",
                )
                for key, item, n in chunk
            ]
        )
    rows.append([InlineKeyboardButton("🎲 No lure", callback_data="catch_lure_none")])
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="catch_cancel")])
    return InlineKeyboardMarkup(rows)


_GAMBLE_PRESETS = [10, 25, 50, 100]


def slots_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"🎰 Spin ({SPIN_COST} 🪙)", callback_data="slots_spin")]]
    )


def gamble_keyboard(user_coins: int) -> InlineKeyboardMarkup:
    btns = [
        InlineKeyboardButton(
            f"{amt} 🪙" if user_coins >= amt else f"💸 {amt}",
            callback_data=f"gamble_bet_{amt}" if user_coins >= amt else "zoo_noop",
        )
        for amt in _GAMBLE_PRESETS
        if amt <= MAX_BET
    ]
    return InlineKeyboardMarkup([btns[:2], btns[2:]])


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


def quests_keyboard(user_id: int, current_arc: int) -> InlineKeyboardMarkup:
    arc_labels = {1: "Arc 1", 2: "Arc 2", 3: "Arc 3", 4: "Arc 4"}
    arc_row = []
    for arc_num, label in arc_labels.items():
        if arc_num == current_arc:
            arc_row.append(InlineKeyboardButton(f"▸ {label} ◂", callback_data="zoo_noop"))
        else:
            arc_row.append(
                InlineKeyboardButton(label, callback_data=f"quest_arc_{user_id}_{arc_num}")
            )
    refresh = InlineKeyboardButton("🔄 Refresh", callback_data=f"quest_arc_{user_id}_{current_arc}")
    return InlineKeyboardMarkup([arc_row, [refresh]])
