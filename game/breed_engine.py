import random
import datetime
from species_data import RARITY_ORDER, get_breed_params


def resolve_offspring(rarity_a: str, rarity_b: str, conn) -> int:
    """
    Return a species_id for the offspring.
    10% chance of bumping up one rarity tier; otherwise inherits one parent's rarity.
    """
    higher = max(rarity_a, rarity_b, key=lambda r: RARITY_ORDER.index(r))
    lower = min(rarity_a, rarity_b, key=lambda r: RARITY_ORDER.index(r))

    bump_chance = 0.10
    higher_idx = RARITY_ORDER.index(higher)

    if random.random() < bump_chance and higher_idx < len(RARITY_ORDER) - 1:
        offspring_rarity = RARITY_ORDER[higher_idx + 1]
    else:
        offspring_rarity = higher if random.random() < 0.7 else lower

    rows = conn.execute("SELECT * FROM species WHERE rarity = ?", (offspring_rarity,)).fetchall()
    return random.choice(rows)["species_id"] if rows else 1


def calc_breed_ready_at(rarity_a: str, rarity_b: str) -> str:
    params = get_breed_params(rarity_a, rarity_b)
    ready = datetime.datetime.utcnow() + datetime.timedelta(hours=params["hours"])
    return ready.isoformat()


def calc_breed_cost(rarity_a: str, rarity_b: str) -> int:
    return get_breed_params(rarity_a, rarity_b)["cost"]


def breed_duration_str(rarity_a: str, rarity_b: str) -> str:
    hours = get_breed_params(rarity_a, rarity_b)["hours"]
    if hours < 24:
        return f"{hours}h"
    return f"{hours // 24}d {hours % 24}h" if hours % 24 else f"{hours // 24}d"
