import random
import uuid

from fastapi import APIRouter, Depends, HTTPException

import db
from config import WILD_EVENT_EXPIRY_MINUTES
from game.constants import LURE_MULTIPLIER, STAT_CAUGHT_MIN, STAT_CAUGHT_MAX
from game.achievements import check_achievements
from deps import get_uid, NULL_CTX

router = APIRouter(tags=["wild_events"])


@router.get("/wild-events/active")
async def get_active_wild_event(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user or not user["group_chat_id"]:
        return None
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM wild_events "
            "WHERE group_chat_id = ? AND caught_by_user_id IS NULL "
            "AND datetime(created_at) > datetime('now', ? || ' minutes') "
            "ORDER BY created_at DESC LIMIT 1",
            (user["group_chat_id"], f"-{WILD_EVENT_EXPIRY_MINUTES}"),
        ).fetchone()
    if not row:
        return None
    species = db.get_species(row["species_id"])
    if not species:
        return None
    return {
        "event_id": row["id"],
        "species_name": species["name"],
        "species_emoji": species["emoji"],
        "rarity": species["rarity"],
        "habitat": species["habitat"],
        "catch_rate": species["catch_rate"],
    }


@router.post("/wild-events/{event_id}/claim")
async def claim_wild_event(event_id: int, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    event = db.get_wild_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event["caught_by_user_id"] is not None:
        raise HTTPException(status_code=400, detail="Already claimed by someone else")

    species = db.get_species(event["species_id"])
    if not species:
        raise HTTPException(status_code=404, detail="Species not found")

    # Check enclosure capacity
    enc_level = db.get_enclosure_level(uid, species["habitat"])
    from game.species_data import ENCLOSURE_LEVELS
    capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
    current = db.get_animal_count_by_habitat(uid, species["habitat"])
    if current >= capacity:
        raise HTTPException(status_code=400, detail=f"Your {species['habitat'].title()} enclosure is full")

    # Requires matching lure
    lure_key = f"lure_{species['habitat']}"
    lure = db.get_oldest_purchase(uid, lure_key)
    if not lure:
        raise HTTPException(status_code=400, detail=f"Need a {species['habitat'].title()} lure to claim this")

    db.consume_purchase(lure["id"])

    catch_rate = min(1.0, species["catch_rate"] * LURE_MULTIPLIER)
    if random.random() >= catch_rate:
        db.claim_wild_event(event_id, -1)
        return {"caught": False, "message": f"🌿 {species['emoji']} {species['name']} got away!"}

    claimed = db.claim_wild_event(event_id, uid)
    if not claimed:
        raise HTTPException(status_code=400, detail="Already claimed by someone else")

    animal_id = str(uuid.uuid4())
    db.add_animal(animal_id, uid, species["species_id"])
    is_shiny = random.random() < 0.015
    if is_shiny:
        db.set_animal_shiny(animal_id)
    db.set_animal_stats(
        animal_id,
        random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX),
        random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX),
        random.randint(STAT_CAUGHT_MIN, STAT_CAUGHT_MAX),
    )

    await check_achievements(uid, "wild_catch", NULL_CTX)
    await check_achievements(uid, "catch", NULL_CTX)

    shiny_str = " ⭐ SHINY!" if is_shiny else ""
    return {
        "caught": True,
        "message": f"⚡ You caught {species['emoji']} {species['name']}!{shiny_str}",
        "emoji": species["emoji"],
        "species_name": species["name"],
        "rarity": species["rarity"],
        "is_shiny": is_shiny,
    }
