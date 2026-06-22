from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from game.achievements import check_achievements
from game.constants import FEED_COST_BY_RARITY, FEED_HUNGER
from deps import get_uid, NULL_CTX

router = APIRouter(tags=["animals"])


def _animal_dict(row) -> dict:
    return dict(row)


@router.get("/animals")
async def list_animals(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return [_animal_dict(a) for a in db.get_animals(uid)]


@router.post("/animals/{animal_id}/feed")
async def feed_animal(animal_id: str, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    animal = db.get_animal(animal_id)
    if not animal or animal["user_id"] != uid:
        raise HTTPException(status_code=404, detail="Animal not found")
    if animal["is_breeding"]:
        raise HTTPException(status_code=400, detail="Animal is breeding")
    if animal["hunger"] >= 100:
        raise HTTPException(status_code=400, detail="Animal is already full")
    feed_cost = FEED_COST_BY_RARITY.get(animal["rarity"], 10)
    if user["coins"] < feed_cost:
        raise HTTPException(
            status_code=400, detail=f"Not enough coins (need {feed_cost})"
        )
    new_hunger = min(100, animal["hunger"] + FEED_HUNGER)
    db.feed_animal(uid, animal_id, new_hunger, feed_cost)
    await check_achievements(uid, "feed", NULL_CTX)
    return {"hunger": new_hunger, "coins_spent": feed_cost}


class NameBody(BaseModel):
    nickname: str


@router.post("/animals/{animal_id}/name")
async def name_animal(animal_id: str, body: NameBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    animal = db.get_animal(animal_id)
    if not animal or animal["user_id"] != uid:
        raise HTTPException(status_code=404, detail="Animal not found")
    nickname = body.nickname.strip()[:32]
    db.set_animal_nickname(animal_id, nickname)
    return {"nickname": nickname}


@router.post("/animals/{animal_id}/sell")
async def sell_animal(animal_id: str, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    animal = db.get_animal(animal_id)
    if not animal or animal["user_id"] != uid:
        raise HTTPException(status_code=404, detail="Animal not found")
    if animal["is_breeding"]:
        raise HTTPException(status_code=400, detail="Cannot sell a breeding animal")
    base = animal["catch_cost"] // 2
    price = max(1, round(base * animal["hunger"] / 100))
    db.sell_animal(uid, animal_id, price)
    await check_achievements(uid, "sell", NULL_CTX)
    return {"coins_earned": price}
