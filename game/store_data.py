STORE_ITEMS: dict[str, dict] = {
    # ── Consumables ───────────────────────────────────────────────────────────
    "mega_feed": {
        "name": "Mega Feed",
        "emoji": "🍖",
        "price": 30,
        "category": "consumable",
        "desc": "Fully restore one animal's hunger to 100",
    },
    "breed_boost": {
        "name": "Breed Boost",
        "emoji": "⚡",
        "price": 80,
        "category": "consumable",
        "desc": "Cut your active breed time by 2 hours — use with /store use breed_boost",
    },
    "lucky_token": {
        "name": "Lucky Token",
        "emoji": "🎯",
        "price": 50,
        "category": "consumable",
        "desc": "2× catch rate on your next /catch — use with /store use lucky_token",
    },
    "mood_booster": {
        "name": "Mood Booster",
        "emoji": "✨",
        "price": 60,
        "category": "consumable",
        "desc": "Double coins on your next mood check-in — use with /store use mood_booster",
    },
    "catch_net": {
        "name": "Catch Net",
        "emoji": "🪤",
        "price": 800,
        "category": "consumable",
        "desc": "Guarantees a legendary encounter and successful catch — use with /store use catch_net",
    },
    "breed_accelerator": {
        "name": "Breed Accelerator",
        "emoji": "🚀",
        "price": 100,
        "category": "consumable",
        "desc": "Halve your remaining breed time — use with /store use breed_accelerator",
    },
    # ── Lures ─────────────────────────────────────────────────────────────────
    "lure_basic": {
        "name": "Basic Lure",
        "emoji": "🎣",
        "price": 25,
        "category": "consumable",
        "desc": "Attract a random animal from any habitat at base catch rate — selected via /catch",
    },
    "lure_woodland": {
        "name": "Woodland Lure",
        "emoji": "🌲",
        "price": 80,
        "category": "consumable",
        "desc": "Attract a Woodland animal with 1.5× catch rate — select via /catch",
    },
    "lure_savanna": {
        "name": "Savanna Lure",
        "emoji": "🌾",
        "price": 80,
        "category": "consumable",
        "desc": "Attract a Savanna animal with 1.5× catch rate — select via /catch",
    },
    "lure_tropical": {
        "name": "Tropical Lure",
        "emoji": "🌴",
        "price": 80,
        "category": "consumable",
        "desc": "Attract a Tropical animal with 1.5× catch rate — select via /catch",
    },
    "lure_aquatic": {
        "name": "Aquatic Lure",
        "emoji": "🐠",
        "price": 80,
        "category": "consumable",
        "desc": "Attract an Aquatic animal with 1.5× catch rate — select via /catch",
    },
    "lure_tundra": {
        "name": "Tundra Lure",
        "emoji": "❄️",
        "price": 80,
        "category": "consumable",
        "desc": "Attract a Tundra animal with 1.5× catch rate — select via /catch",
    },
    "lure_mythic": {
        "name": "Mythic Lure",
        "emoji": "🌟",
        "price": 200,
        "category": "consumable",
        "desc": "Attract a Mythic animal with 1.5× catch rate — select via /catch",
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
CONSUMABLES = {
    k: v
    for k, v in STORE_ITEMS.items()
    if v["category"] == "consumable" and not k.startswith("lure_")
}
COSMETICS = {k: v for k, v in STORE_ITEMS.items() if v["category"] == "cosmetic"}
