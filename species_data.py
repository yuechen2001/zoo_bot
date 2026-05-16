SPECIES = [
    # Common — encounter 60%, catch 90%, cost 20, decay 3/tick
    {"name": "Mouse",   "emoji": "🐭", "rarity": "common",    "catch_rate": 0.90, "catch_cost": 20,  "hunger_decay": 3,  "breed_time_hrs": 6},
    {"name": "Frog",    "emoji": "🐸", "rarity": "common",    "catch_rate": 0.90, "catch_cost": 20,  "hunger_decay": 3,  "breed_time_hrs": 6},
    {"name": "Hamster", "emoji": "🐹", "rarity": "common",    "catch_rate": 0.90, "catch_cost": 20,  "hunger_decay": 3,  "breed_time_hrs": 6},
    {"name": "Duck",    "emoji": "🦆", "rarity": "common",    "catch_rate": 0.90, "catch_cost": 20,  "hunger_decay": 3,  "breed_time_hrs": 6},
    {"name": "Snail",   "emoji": "🐌", "rarity": "common",    "catch_rate": 0.90, "catch_cost": 20,  "hunger_decay": 3,  "breed_time_hrs": 6},

    # Rare — encounter 25%, catch 60%, cost 60, decay 5/tick
    {"name": "Cat",     "emoji": "🐱", "rarity": "rare",      "catch_rate": 0.60, "catch_cost": 60,  "hunger_decay": 5,  "breed_time_hrs": 12},
    {"name": "Dog",     "emoji": "🐶", "rarity": "rare",      "catch_rate": 0.60, "catch_cost": 60,  "hunger_decay": 5,  "breed_time_hrs": 12},
    {"name": "Bunny",   "emoji": "🐰", "rarity": "rare",      "catch_rate": 0.60, "catch_cost": 60,  "hunger_decay": 5,  "breed_time_hrs": 12},
    {"name": "Fox",     "emoji": "🦊", "rarity": "rare",      "catch_rate": 0.60, "catch_cost": 60,  "hunger_decay": 5,  "breed_time_hrs": 12},
    {"name": "Penguin", "emoji": "🐧", "rarity": "rare",      "catch_rate": 0.60, "catch_cost": 60,  "hunger_decay": 5,  "breed_time_hrs": 12},

    # Epic — encounter 12%, catch 35%, cost 80, decay 7/tick
    {"name": "Panda",   "emoji": "🐼", "rarity": "epic",      "catch_rate": 0.35, "catch_cost": 80,  "hunger_decay": 7,  "breed_time_hrs": 28},
    {"name": "Bear",    "emoji": "🐻", "rarity": "epic",      "catch_rate": 0.35, "catch_cost": 80,  "hunger_decay": 7,  "breed_time_hrs": 28},
    {"name": "Koala",   "emoji": "🐨", "rarity": "epic",      "catch_rate": 0.35, "catch_cost": 80,  "hunger_decay": 7,  "breed_time_hrs": 28},
    {"name": "Lion",    "emoji": "🦁", "rarity": "epic",      "catch_rate": 0.35, "catch_cost": 80,  "hunger_decay": 7,  "breed_time_hrs": 28},
    {"name": "Tiger",   "emoji": "🐯", "rarity": "epic",      "catch_rate": 0.35, "catch_cost": 80,  "hunger_decay": 7,  "breed_time_hrs": 28},

    # Legendary — encounter 3%, catch 10%, cost 200, decay 10/tick
    {"name": "Unicorn",  "emoji": "🦄", "rarity": "legendary", "catch_rate": 0.10, "catch_cost": 200, "hunger_decay": 10, "breed_time_hrs": 48},
    {"name": "Dragon",   "emoji": "🐉", "rarity": "legendary", "catch_rate": 0.10, "catch_cost": 200, "hunger_decay": 10, "breed_time_hrs": 48},
    {"name": "Peacock",  "emoji": "🦚", "rarity": "legendary", "catch_rate": 0.10, "catch_cost": 200, "hunger_decay": 10, "breed_time_hrs": 48},
    {"name": "Eagle",    "emoji": "🦅", "rarity": "legendary", "catch_rate": 0.10, "catch_cost": 200, "hunger_decay": 10, "breed_time_hrs": 48},
    {"name": "Giraffe",  "emoji": "🦒", "rarity": "legendary", "catch_rate": 0.10, "catch_cost": 200, "hunger_decay": 10, "breed_time_hrs": 48},
    {"name": "Elephant", "emoji": "🐘", "rarity": "legendary", "catch_rate": 0.10, "catch_cost": 200, "hunger_decay": 10, "breed_time_hrs": 48},
]

# Weighted encounter probabilities per rarity
ENCOUNTER_WEIGHTS = {
    "common":    60,
    "rare":      25,
    "epic":      12,
    "legendary":  3,
}

RARITY_ORDER = ["common", "rare", "epic", "legendary"]

RARITY_LABELS = {
    "common":    "Common ⬜",
    "rare":      "Rare 🟦",
    "epic":      "Epic 🟪",
    "legendary": "Legendary 🟨",
}

# Breed costs by rarity pair (sorted tuple → cost, hours)
BREED_TABLE = {
    ("common",    "common"):    {"cost": 50,  "hours": 6},
    ("common",    "rare"):      {"cost": 120, "hours": 12},
    ("rare",      "rare"):      {"cost": 200, "hours": 18},
    ("common",    "epic"):      {"cost": 350, "hours": 28},
    ("rare",      "epic"):      {"cost": 350, "hours": 28},
    ("epic",      "epic"):      {"cost": 500, "hours": 36},
    ("common",    "legendary"): {"cost": 800, "hours": 48},
    ("rare",      "legendary"): {"cost": 800, "hours": 48},
    ("epic",      "legendary"): {"cost": 800, "hours": 48},
    ("legendary", "legendary"): {"cost": 800, "hours": 48},
}


def get_breed_params(rarity_a, rarity_b):
    key = tuple(sorted([rarity_a, rarity_b], key=lambda r: RARITY_ORDER.index(r)))
    return BREED_TABLE.get(key, {"cost": 200, "hours": 24})
