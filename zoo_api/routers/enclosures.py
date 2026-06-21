from fastapi import APIRouter, Depends, HTTPException

import db
from game.species_data import ENCLOSURE_LEVELS, HABITATS, MAX_ENCLOSURE_LEVEL
from game.achievements import check_achievements
from deps import get_uid, NULL_CTX

router = APIRouter(tags=["enclosures"])


@router.get("/enclosures")
async def list_enclosures(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    enc_levels = db.get_enclosures(uid)
    result = {}
    for habitat, info in HABITATS.items():
        level = enc_levels.get(habitat, 1)
        data = ENCLOSURE_LEVELS[level]
        next_data = ENCLOSURE_LEVELS.get(level + 1)
        animal_count = db.get_animal_count_by_habitat(uid, habitat)
        result[habitat] = {
            "name": info["name"],
            "emoji": info["emoji"],
            "level": level,
            "max_level": MAX_ENCLOSURE_LEVEL,
            "capacity": data["capacity"],
            "animals_used": animal_count,
            "coins_per_animal_hr": data["coins_per_animal_hr"],
            "breed_bonus": data["breed_bonus"],
            "catch_rate_bonus": data["catch_rate_bonus"],
            "upgrade_cost": next_data["upgrade_cost"] if next_data else None,
        }
    return result


@router.post("/enclosures/{habitat}/upgrade")
async def upgrade_enclosure(habitat: str, uid: int = Depends(get_uid)):
    if habitat not in HABITATS:
        raise HTTPException(status_code=400, detail="Invalid habitat")
    result = db.upgrade_enclosure(uid, habitat)
    if result == "max_level":
        raise HTTPException(status_code=400, detail="Already at max level")
    if result == "insufficient_coins":
        raise HTTPException(status_code=400, detail="Not enough coins")
    await check_achievements(uid, "enclosure", NULL_CTX)
    new_level = db.get_enclosure_level(uid, habitat)
    return {"habitat": habitat, "new_level": new_level}


@router.post("/enclosures/collect")
async def collect_enclosure_income(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    amount = db.collect_enclosure_coins(uid)
    return {"coins_collected": amount}
