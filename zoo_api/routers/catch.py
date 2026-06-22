import random
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from game.catch_engine import pick_species, roll_catch, roll_encounter
from game.constants import LURE_MULTIPLIER, NO_LURE_COST
from game.species_data import ENCLOSURE_LEVELS, HABITATS
from game.achievements import check_achievements
from deps import get_uid, NULL_CTX

router = APIRouter(tags=["catch"])

LURE_KEYS = {f"lure_{h}" for h in HABITATS}
STAT_CAUGHT_MIN = 35
STAT_CAUGHT_MAX = 75


class CatchBody(BaseModel):
    lure_key: str | None = None  # e.g. "lure_woodland", or None for no lure


@router.post("/catch/start")
async def start_catch(body: CatchBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    habitat: str | None = None
    lure_key = body.lure_key
    base_catch_multiplier = 1.0
    catch_cost = NO_LURE_COST

    if lure_key:
        if lure_key not in LURE_KEYS:
            raise HTTPException(status_code=400, detail="Invalid lure key")
        item_counts = db.get_item_counts(uid)
        if item_counts.get(lure_key, 0) < 1:
            raise HTTPException(
                status_code=400, detail="No lure of that type in inventory"
            )
        habitat = lure_key.removeprefix("lure_")
        # Consume lure
        purchase_row = db.get_oldest_purchase(uid, lure_key)
        if purchase_row:
            db.consume_purchase(purchase_row["id"])
        base_catch_multiplier = LURE_MULTIPLIER

    if user["coins"] < catch_cost:
        raise HTTPException(
            status_code=400, detail=f"Need {catch_cost} coins to search"
        )

    # Apply power-ups
    catch_net = bool(user["catch_net_active"])
    lucky = bool(user["lucky_catch_active"])
    rare_magnet = bool(user["rare_magnet_active"])
    epic_magnet = bool(user["epic_magnet_active"])

    if catch_net:
        rarity = "legendary"
        base_catch_multiplier = 999.0
        db.set_catch_net(uid, False)
    elif epic_magnet:
        rarity = random.choice(["epic", "legendary"])
        db.set_epic_magnet(uid, False)
    elif rare_magnet:
        rolled = roll_encounter()
        rarity = rolled if rolled in ("rare", "epic", "legendary") else "rare"
        db.set_rare_magnet(uid, False)
    else:
        rarity = roll_encounter()

    if lucky:
        base_catch_multiplier *= 2.0
        db.set_lucky_catch(uid, False)

    with db.get_conn() as conn:
        species = pick_species(rarity, conn, habitat)

    if not species:
        db.deduct_coins(uid, catch_cost)
        return {"caught": False, "reason": "No species found for that habitat/rarity"}

    enc_level = db.get_enclosure_level(uid, species["habitat"])
    enc_bonus = ENCLOSURE_LEVELS[enc_level].get("catch_rate_bonus", 0.0)
    effective_rate = min(1.0, species["catch_rate"] * base_catch_multiplier + enc_bonus)
    caught = roll_catch(effective_rate)

    db.deduct_coins(uid, catch_cost)

    if not caught:
        return {
            "caught": False,
            "species": dict(species),
            "rarity": rarity,
            "catch_rate": round(effective_rate, 3),
        }

    # Roll shiny
    is_shiny = random.random() < 0.015

    # Roll stats
    stat_speed = random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX)
    stat_rarity = random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX)
    stat_temperament = random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX)

    animal_id = str(uuid.uuid4())
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO animals (animal_id, user_id, species_id, hunger, is_shiny, "
            "stat_speed, stat_rarity, stat_temperament) VALUES (?, ?, ?, 100, ?, ?, ?, ?)",
            (
                animal_id,
                uid,
                species["species_id"],
                is_shiny,
                stat_speed,
                stat_rarity,
                stat_temperament,
            ),
        )

    await check_achievements(uid, "catch", NULL_CTX)

    return {
        "caught": True,
        "animal_id": animal_id,
        "species": dict(species),
        "rarity": rarity,
        "is_shiny": is_shiny,
        "stats": {
            "speed": stat_speed,
            "rarity": stat_rarity,
            "temperament": stat_temperament,
        },
    }
