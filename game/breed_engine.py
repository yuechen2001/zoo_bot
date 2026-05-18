import random
import datetime
from game.species_data import RARITY_ORDER, get_breed_params


# (common, rare, epic, legendary) weights per sorted parent rarity pair.
# Breeding complements /catch — epic/legendary from low-tier pairs is intentionally rare.
_RARITY_WEIGHTS: dict[tuple[str, str], tuple] = {
    ("common", "common"): (85, 13, 1.5, 0.5),
    ("common", "rare"): (42, 52, 5, 1),
    ("rare", "rare"): (18, 72, 8, 2),
    ("common", "epic"): (25, 40, 30, 5),
    ("rare", "epic"): (12, 33, 47, 8),
    ("epic", "epic"): (5, 18, 65, 12),
    ("common", "legendary"): (15, 32, 38, 15),
    ("rare", "legendary"): (8, 20, 50, 22),
    ("epic", "legendary"): (3, 10, 47, 40),
    ("legendary", "legendary"): (5, 15, 40, 40),
}


def resolve_offspring(rarity_a: str, rarity_b: str, get_candidates) -> int:
    """Return a species_id for the offspring using weighted rarity distribution.

    get_candidates(rarity) must return a list of species rows for that rarity.
    """
    a, b = sorted([rarity_a, rarity_b], key=lambda r: RARITY_ORDER.index(r))
    weights = _RARITY_WEIGHTS[(a, b)]
    offspring_rarity = random.choices(RARITY_ORDER, weights=weights, k=1)[0]
    rows = get_candidates(offspring_rarity)
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
    ready = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(
        hours=hours
    )
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
