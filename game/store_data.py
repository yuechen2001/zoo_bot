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
        "desc": "Cut your active breed time by 2 hours",
    },
    "lucky_token": {
        "name": "Lucky Token",
        "emoji": "🎯",
        "price": 50,
        "category": "consumable",
        "desc": "Your next /catch attempt has 2× catch rate",
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

CONSUMABLES = {k: v for k, v in STORE_ITEMS.items() if v["category"] == "consumable"}
COSMETICS = {k: v for k, v in STORE_ITEMS.items() if v["category"] == "cosmetic"}
