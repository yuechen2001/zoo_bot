import math

EMOJI_BASE_COINS = {
    "😢": 10,
    "😐": 20,
    "🙂": 35,
    "😄": 55,
    "🤩": 80,
}

EMOJI_HAPPINESS_DELTA = {
    "😢": -5,
    "😐": 0,
    "🙂": +3,
    "😄": +5,
    "🤩": +10,
}

EMOJI_LABELS = {
    "😢": "Rough day",
    "😐": "Meh",
    "🙂": "Pretty good",
    "😄": "Great",
    "🤩": "Amazing",
}


def get_streak_multiplier(streak_windows: int) -> float:
    if streak_windows >= 30:
        return 3.0
    if streak_windows >= 16:
        return 2.0
    if streak_windows >= 8:
        return 1.5
    if streak_windows >= 4:
        return 1.25
    return 1.0


def calc_coins(emoji: str, streak_windows: int) -> int:
    base = EMOJI_BASE_COINS.get(emoji, 20)
    multiplier = get_streak_multiplier(streak_windows)
    return math.floor(base * multiplier)


def streak_label(windows: int) -> str:
    w = f"{windows} window{'s' if windows != 1 else ''}"
    if windows == 0:
        return "No streak yet"
    if windows < 4:
        return f"{w} (1.0x)"
    if windows < 8:
        return f"{w} (1.25x)"
    if windows < 16:
        return f"{w} (1.5x)"
    if windows < 30:
        return f"{w} (2.0x)"
    return f"{w} (3.0x 🔥)"
