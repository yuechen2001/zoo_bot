import random
from species_data import ENCOUNTER_WEIGHTS


def roll_encounter() -> str:
    """Weighted random rarity roll."""
    rarities = list(ENCOUNTER_WEIGHTS.keys())
    weights = [ENCOUNTER_WEIGHTS[r] for r in rarities]
    return random.choices(rarities, weights=weights, k=1)[0]


def pick_species(rarity: str, conn, habitat: str | None = None) -> object:
    if habitat:
        rows = conn.execute(
            "SELECT * FROM species WHERE rarity = ? AND habitat = ?", (rarity, habitat)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM species WHERE rarity = ?", (rarity,)).fetchall()
    return random.choice(rows) if rows else None


def roll_catch(catch_rate: float) -> bool:
    return random.random() < catch_rate
