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


def _hunger_adjusted_hours(base_hours: float, hunger_a: int, hunger_b: int) -> float:
    """Scale breed time by parent hunger. Full hunger (100) = base time; zero hunger = 2× base."""
    avg_hunger = (hunger_a + hunger_b) / 2.0
    return base_hours * (2.0 - avg_hunger / 100.0)


def calc_breed_ready_at(
    rarity_a: str,
    rarity_b: str,
    hunger_a: int = 100,
    hunger_b: int = 100,
    habitat_bonus: float = 0.0,
) -> str:
    params = get_breed_params(rarity_a, rarity_b)
    hours = _hunger_adjusted_hours(params["hours"], hunger_a, hunger_b)
    hours *= max(0.0, 1.0 - habitat_bonus)
    ready = datetime.datetime.utcnow() + datetime.timedelta(hours=hours)
    return ready.isoformat()


def calc_breed_cost(rarity_a: str, rarity_b: str) -> int:
    return get_breed_params(rarity_a, rarity_b)["cost"]


def breed_duration_str(
    rarity_a: str,
    rarity_b: str,
    hunger_a: int = 100,
    hunger_b: int = 100,
    habitat_bonus: float = 0.0,
) -> str:
    params = get_breed_params(rarity_a, rarity_b)
    hours = _hunger_adjusted_hours(params["hours"], hunger_a, hunger_b)
    hours *= max(0.0, 1.0 - habitat_bonus)
    if hours < 1:
        minutes = round(hours * 60)
        return f"{minutes}m"
    h = int(hours)
    m = round((hours - h) * 60)
    if h >= 24:
        days = h // 24
        rem_h = h % 24
        return f"{days}d {rem_h}h" if rem_h else f"{days}d"
    return f"{h}h {m}m" if m else f"{h}h"
