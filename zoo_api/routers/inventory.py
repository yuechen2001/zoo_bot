from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from game.store_data import STORE_ITEMS
from deps import get_uid

router = APIRouter(tags=["inventory"])

# Items that toggle a user flag rather than being "consumed" immediately
_FLAG_ITEMS = {
    "lucky_token": db.set_lucky_catch,
    "mood_booster": db.set_mood_booster,
    "catch_net": db.set_catch_net,
    "rare_magnet": db.set_rare_magnet,
    "epic_magnet": db.set_epic_magnet,
    "streak_shield": db.set_streak_shield,
}


@router.get("/inventory")
async def get_inventory(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    item_counts = db.get_item_counts(uid)
    owned_titles = db.get_owned_title_keys(uid)
    items = {k: v for k, v in item_counts.items() if not k.startswith("title_")}
    lures = {k: v for k, v in item_counts.items() if k.startswith("lure_")}
    consumables = {k: v for k, v in items.items() if not k.startswith("lure_")}
    return {
        "consumables": consumables,
        "lures": lures,
        "titles_owned": list(owned_titles),
        "active_title": user["active_title"],
    }


class UseBody(BaseModel):
    item_key: str


@router.post("/inventory/use")
async def use_item(body: UseBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    item = STORE_ITEMS.get(body.item_key)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown item")

    item_counts = db.get_item_counts(uid)
    if item_counts.get(body.item_key, 0) < 1:
        raise HTTPException(status_code=400, detail="Item not in inventory")

    purchase_row = db.get_oldest_purchase(uid, body.item_key)
    if not purchase_row:
        raise HTTPException(status_code=400, detail="Item not found in purchases")

    if body.item_key in _FLAG_ITEMS:
        db.consume_purchase(purchase_row["id"])
        _FLAG_ITEMS[body.item_key](uid, True)
        return {"activated": body.item_key}

    raise HTTPException(status_code=400, detail="This item cannot be activated here")


class EquipBody(BaseModel):
    title_key: str | None = None


@router.post("/inventory/equip")
async def equip_title(body: EquipBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.title_key is not None:
        owned = db.get_owned_title_keys(uid)
        if body.title_key not in owned:
            raise HTTPException(status_code=400, detail="Title not owned")
    db.set_active_title(uid, body.title_key)
    return {"active_title": body.title_key}
