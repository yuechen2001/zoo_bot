STORE_ITEMS: dict[str, dict] = {
    # ── Consumables ───────────────────────────────────────────────────────────
    "mega_feed": {
        "name": "Mega Feed",
        "emoji": "🍖",
        "price": 30,
        "category": "item",
        "desc": "Fully restore one animal's hunger to 100",
    },
    "breed_boost": {
        "name": "Breed Boost",
        "emoji": "⚡",
        "price": 80,
        "category": "item",
        "desc": "Cut your active breed time by 2 hours — activate from /inventory",
    },
    "lucky_token": {
        "name": "Lucky Token",
        "emoji": "🎯",
        "price": 80,
        "category": "item",
        "desc": "2× catch rate on your next /catch — activate from /inventory",
    },
    "mood_booster": {
        "name": "Mood Booster",
        "emoji": "✨",
        "price": 60,
        "category": "item",
        "desc": "Double coins on your next mood check-in — activate from /inventory",
    },
    "catch_net": {
        "name": "Catch Net",
        "emoji": "🪤",
        "price": 600,
        "category": "item",
        "desc": "Guarantees a legendary encounter and successful catch — activate from /inventory",
    },
    "rare_magnet": {
        "name": "Rare Magnet",
        "emoji": "🧲",
        "price": 100,
        "category": "item",
        "desc": "Guarantee a rare-or-higher encounter on your next /catch — activate from /inventory",
    },
    # ── Lures ─────────────────────────────────────────────────────────────────
    "lure_woodland": {
        "name": "Woodland Lure",
        "emoji": "🌲",
        "price": 60,
        "category": "item",
        "desc": "Attract a Woodland animal with 1.5× catch rate — select when using /catch",
    },
    "lure_savanna": {
        "name": "Savanna Lure",
        "emoji": "🌾",
        "price": 60,
        "category": "item",
        "desc": "Attract a Savanna animal with 1.5× catch rate — select when using /catch",
    },
    "lure_tropical": {
        "name": "Tropical Lure",
        "emoji": "🌴",
        "price": 60,
        "category": "item",
        "desc": "Attract a Tropical animal with 1.5× catch rate — select when using /catch",
    },
    "lure_aquatic": {
        "name": "Aquatic Lure",
        "emoji": "🐠",
        "price": 60,
        "category": "item",
        "desc": "Attract an Aquatic animal with 1.5× catch rate — select when using /catch",
    },
    "lure_tundra": {
        "name": "Tundra Lure",
        "emoji": "❄️",
        "price": 60,
        "category": "item",
        "desc": "Attract a Tundra animal with 1.5× catch rate — select when using /catch",
    },
    "lure_mythic": {
        "name": "Mythic Lure",
        "emoji": "🌟",
        "price": 150,
        "category": "item",
        "desc": "Attract a Mythic animal with 1.5× catch rate — select when using /catch",
    },
    # ── Cosmetics ─────────────────────────────────────────────────────────────
    "title_keeper": {
        "name": "Zookeeper",
        "emoji": "🎖",
        "price": 200,
        "category": "cosmetic",
        "desc": "Display the title 'Zookeeper' in your zoo",
    },
    "title_whisperer": {
        "name": "Animal Whisperer",
        "emoji": "🌿",
        "price": 500,
        "category": "cosmetic",
        "desc": "Display the title 'Animal Whisperer' in your zoo",
    },
    "title_legend": {
        "name": "Zoo Legend",
        "emoji": "👑",
        "price": 1000,
        "category": "cosmetic",
        "desc": "Display the title 'Zoo Legend' in your zoo",
    },
}

LURES = {k: v for k, v in STORE_ITEMS.items() if k.startswith("lure_")}
ITEMS = {
    k: v for k, v in STORE_ITEMS.items() if v["category"] == "item" and not k.startswith("lure_")
}
COSMETICS = {k: v for k, v in STORE_ITEMS.items() if v["category"] == "cosmetic"}
