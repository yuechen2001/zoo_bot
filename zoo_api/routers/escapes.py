import datetime
import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from game.constants import ESCAPE_LURE_SUCCESS_RATE, ESCAPE_CHASE_SUCCESS_RATE, ESCAPE_RELEASE_REFUND_RATE
from deps import get_uid

router = APIRouter(tags=["escapes"])


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


@router.get("/escapes/pending")
async def get_pending_escape(uid: int = Depends(get_uid)):
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM animal_escapes WHERE user_id = ? AND resolved = 0 ORDER BY escaped_at DESC LIMIT 1",
            (uid,),
        ).fetchone()
    if not row:
        return None
    now = _now()
    if now > datetime.datetime.fromisoformat(row["expires_at"]):
        return None
    animal = db.get_animal(row["animal_id"])
    if not animal:
        return None
    return {
        "escape_id": row["escape_id"],
        "animal_id": row["animal_id"],
        "emoji": animal["emoji"],
        "name": animal["nickname"] or animal["species_name"],
        "habitat": animal["habitat"],
        "expires_at": row["expires_at"],
    }


class ResolveBody(BaseModel):
    action: str  # "lure" | "chase" | "release"


@router.post("/escapes/{escape_id}/resolve")
async def resolve_escape(escape_id: int, body: ResolveBody, uid: int = Depends(get_uid)):
    escape = db.get_escape(escape_id)
    if not escape:
        raise HTTPException(status_code=404, detail="Escape not found")
    if escape["user_id"] != uid:
        raise HTTPException(status_code=403, detail="Not your animal")
    if escape["resolved"] != 0:
        raise HTTPException(status_code=400, detail="Already resolved")
    now = _now()
    if now > datetime.datetime.fromisoformat(escape["expires_at"]):
        raise HTTPException(status_code=400, detail="Window has expired")

    animal = db.get_animal(escape["animal_id"])
    if not animal:
        db.resolve_escape(escape_id, 2)
        raise HTTPException(status_code=404, detail="Animal no longer exists")

    name = animal["nickname"] or animal["species_name"]
    emoji = animal["emoji"]

    if body.action == "lure":
        lure_key = f"lure_{animal['habitat']}"
        purchase = db.get_oldest_purchase(uid, lure_key)
        if not purchase:
            raise HTTPException(status_code=400, detail=f"No {animal['habitat']} lure in inventory")
        db.consume_purchase(purchase["id"])
        if random.random() < ESCAPE_LURE_SUCCESS_RATE:
            db.resolve_escape(escape_id, 1)
            return {"success": True, "message": f"🎣 {emoji} {name} was lured back!"}
        else:
            db.delete_animal(escape["animal_id"])
            db.resolve_escape(escape_id, 2)
            return {"success": False, "message": f"😢 The lure failed — {emoji} {name} got away!"}

    elif body.action == "chase":
        if random.random() < ESCAPE_CHASE_SUCCESS_RATE:
            db.resolve_escape(escape_id, 1)
            return {"success": True, "message": f"🏃 You caught up to {emoji} {name}!"}
        else:
            db.delete_animal(escape["animal_id"])
            db.resolve_escape(escape_id, 2)
            return {"success": False, "message": f"😢 {emoji} {name} was too fast and got away!"}

    elif body.action == "release":
        refund = max(1, round(animal["catch_cost"] // 2 * ESCAPE_RELEASE_REFUND_RATE))
        db.add_coins(uid, refund)
        db.delete_animal(escape["animal_id"])
        db.resolve_escape(escape_id, 3)
        return {"success": True, "message": f"🕊️ {emoji} {name} was set free. +{refund} 🪙"}

    raise HTTPException(status_code=400, detail="Invalid action")
