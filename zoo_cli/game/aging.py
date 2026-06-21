import datetime

JUVENILE_DAYS = 3
ELDER_DAYS = 30

STAGE_EMOJI = {
    "juvenile": "🐣",
    "adult": "🐾",
    "elder": "👴",
}

INCOME_MULTIPLIER = {
    "juvenile": 0.8,
    "adult": 1.0,
    "elder": 1.6,
}

BREED_TIME_MULTIPLIER = {
    "juvenile": 1.25,
    "adult": 1.0,
    "elder": 1.0,
}


def get_stage(caught_at: str) -> str:
    try:
        caught = datetime.datetime.fromisoformat(caught_at)
        if caught.tzinfo is None:
            caught = caught.replace(tzinfo=datetime.timezone.utc)
    except (ValueError, TypeError):
        return "adult"
    age_days = (datetime.datetime.now(datetime.timezone.utc) - caught).total_seconds() / 86400
    if age_days < JUVENILE_DAYS:
        return "juvenile"
    if age_days < ELDER_DAYS:
        return "adult"
    return "elder"
