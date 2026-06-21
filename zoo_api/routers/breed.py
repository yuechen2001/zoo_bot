import datetime
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from game.breed_engine import calc_breed_cost, calc_breed_ready_at, resolve_offspring
from game.constants import STAT_INHERIT_NOISE
from game.species_data import ENCLOSURE_LEVELS
from game.achievements import check_achievements
from deps import get_uid, NULL_CTX

router = APIRouter(tags=["breed"])


class BreedBody(BaseModel):
    animal_a_id: str
    animal_b_id: str


@router.get("/breed")
async def get_breed_status(uid: int = Depends(get_uid)):
    breed = db.get_active_breed(uid)
    if not breed:
        return {"active": False}
    ready = datetime.datetime.fromisoformat(breed["ready_at"])
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    return {
        "active": True,
        "breed_id": breed["id"],
        "emoji_a": breed["emoji_a"],
        "name_a": breed["name_a"],
        "emoji_b": breed["emoji_b"],
        "name_b": breed["name_b"],
        "ready_at": breed["ready_at"],
        "is_ready": now >= ready,
        "collected": bool(breed["collected"]),
    }


@router.post("/breed/start")
async def start_breed(body: BreedBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if db.get_active_breed(uid):
        raise HTTPException(status_code=400, detail="Already breeding")

    animal_a = db.get_animal(body.animal_a_id)
    animal_b = db.get_animal(body.animal_b_id)

    for a, label in [(animal_a, "A"), (animal_b, "B")]:
        if not a or a["user_id"] != uid:
            raise HTTPException(status_code=404, detail=f"Animal {label} not found")
        if a["is_breeding"]:
            raise HTTPException(status_code=400, detail=f"Animal {label} is already breeding")

    if body.animal_a_id == body.animal_b_id:
        raise HTTPException(status_code=400, detail="Cannot breed an animal with itself")

    cost = calc_breed_cost(animal_a["rarity"], animal_b["rarity"])
    if user["coins"] < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} coins to breed")

    enc_level = db.get_enclosure_level(uid, animal_a["habitat"])
    habitat_bonus = ENCLOSURE_LEVELS[enc_level].get("breed_bonus", 0.0)

    ready_at = calc_breed_ready_at(
        animal_a["rarity"], animal_b["rarity"],
        animal_a["hunger"], animal_b["hunger"],
        habitat_bonus,
        animal_a["stat_speed"], animal_b["stat_speed"],
    )

    def get_candidates(rarity):
        with db.get_conn() as conn:
            return conn.execute(
                "SELECT * FROM species WHERE rarity = ? AND is_special = 0", (rarity,)
            ).fetchall()

    offspring_species_id = resolve_offspring(
        animal_a["rarity"], animal_b["rarity"],
        get_candidates,
        animal_a["stat_rarity"], animal_b["stat_rarity"],
    )

    db.start_breed(uid, body.animal_a_id, body.animal_b_id, offspring_species_id, ready_at, cost)
    return {"ready_at": ready_at, "cost": cost}


@router.post("/breed/collect")
async def collect_breed(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    breed = db.get_active_breed(uid)
    if not breed:
        raise HTTPException(status_code=404, detail="No active breed")
    if breed["collected"]:
        raise HTTPException(status_code=400, detail="Already collected")

    ready = datetime.datetime.fromisoformat(breed["ready_at"])
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if now < ready:
        raise HTTPException(status_code=400, detail="Breed not ready yet")

    # Inherit stats with noise
    parent_a = db.get_animal(breed["parent_a"])
    parent_b = db.get_animal(breed["parent_b"])

    def _inherit(stat_a, stat_b):
        avg = (stat_a + stat_b) / 2
        noise = random.randint(-STAT_INHERIT_NOISE, STAT_INHERIT_NOISE)
        return max(1, min(100, round(avg + noise)))

    stat_speed = _inherit(parent_a["stat_speed"], parent_b["stat_speed"])
    stat_rarity = _inherit(parent_a["stat_rarity"], parent_b["stat_rarity"])
    stat_temperament = _inherit(parent_a["stat_temperament"], parent_b["stat_temperament"])
    is_shiny = random.random() < 0.015

    animal_id = str(uuid.uuid4())
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO animals (animal_id, user_id, species_id, hunger, is_shiny, "
            "stat_speed, stat_rarity, stat_temperament) VALUES (?, ?, ?, 100, ?, ?, ?, ?)",
            (animal_id, uid, breed["offspring_species_id"], is_shiny, stat_speed, stat_rarity, stat_temperament),
        )
        conn.execute(
            "UPDATE animals SET is_breeding = 0 WHERE animal_id IN (?, ?)",
            (breed["parent_a"], breed["parent_b"]),
        )
        conn.execute("UPDATE breeding_queue SET collected = 1 WHERE id = ?", (breed["id"],))

    offspring = db.get_animal(animal_id)
    await check_achievements(uid, "breed", NULL_CTX)

    return {
        "animal_id": animal_id,
        "species_id": breed["offspring_species_id"],
        "emoji": offspring["emoji"] if offspring else "",
        "species_name": offspring["species_name"] if offspring else "",
        "rarity": offspring["rarity"] if offspring else "",
        "is_shiny": is_shiny,
        "stats": {"speed": stat_speed, "rarity": stat_rarity, "temperament": stat_temperament},
    }
