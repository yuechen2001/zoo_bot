# Catch / lures
LURE_MULTIPLIER = 1.5

# Feed
FEED_COST_BY_RARITY = {"common": 5, "rare": 10, "epic": 15, "legendary": 20}
FEED_HUNGER = 40

# Slots
SPIN_COST = 10
WIN_3 = 150
WIN_2 = 10
SYMBOLS = ["🐭", "🐸", "🐱", "🦊", "🐼", "🦄"]

# Gamble
MAX_BET = 200

# Foot massage
MASSAGE_COST = 25
MASSAGE_DURATION_HOURS = 1
MASSAGE_COOLDOWN_HOURS = 4

# Trivia
TRIVIA_COOLDOWN_MINUTES = 15
TRIVIA_WINDOW_MINUTES = 10
COINS_CORRECT = 40
COINS_WRONG = 5

# Daily
DAILY_COOLDOWN_HOURS = 24
DAILY_STREAK_EXPIRY_HOURS = 48
DAILY_TIERS = [
    (14, 150),
    (7, 100),
    (3, 75),
    (1, 50),
]

# Invest
MIN_INVEST = 10

# Breed boost / accelerator
BREED_BOOST_HOURS = 2  # hours subtracted by Breed Boost item

# Wild events — rarity weights for random encounter roll [common, rare, epic, legendary]
WILD_EVENT_RARITY_WEIGHTS = [20, 40, 30, 10]

# Power-up display labels for /zoo — (user_flag_column, display_label)
POWERUP_LABELS = [
    ("lucky_catch_active", "🎯 Lucky"),
    ("mood_booster_active", "✨ Mood Boost"),
    ("catch_net_active", "🪤 Catch Net"),
    ("rare_magnet_active", "🧲 Rare Magnet"),
    ("epic_magnet_active", "💜 Epic Magnet"),
    ("streak_shield_active", "🛡️ Streak Shield"),
]
