from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from game.store_data import STORE_ITEMS
from game.achievements import check_achievements
from deps import get_uid, NULL_CTX

router = APIRouter(tags=["store"])


@router.get("/store")
async def get_store(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    item_counts = db.get_item_counts(uid)
    owned_titles = db.get_owned_title_keys(uid)
    items = []
    for key, item in STORE_ITEMS.items():
        if item.get("is_special"):
            continue
        entry = {**item, "key": key}
        if item["category"] == "cosmetic":
            entry["owned"] = key in owned_titles
        else:
            entry["quantity"] = item_counts.get(key, 0)
        items.append(entry)
    return items


class BuyBody(BaseModel):
    item_key: str


@router.post("/store/buy")
async def buy_item(body: BuyBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    item = STORE_ITEMS.get(body.item_key)
    if not item or item.get("is_special"):
        raise HTTPException(status_code=404, detail="Item not found")

    if item["category"] == "cosmetic":
        if db.has_purchased(uid, body.item_key):
            raise HTTPException(status_code=400, detail="Already owned")

    if user["coins"] < item["price"]:
        raise HTTPException(status_code=400, detail=f"Need {item['price']} coins")

    db.deduct_coins(uid, item["price"])
    db.record_purchase(uid, body.item_key)
    await check_achievements(uid, "store", NULL_CTX)
    return {"item_key": body.item_key, "coins_spent": item["price"]}
