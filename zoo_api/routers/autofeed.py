from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from deps import get_uid

router = APIRouter(tags=["autofeed"])


@router.get("/autofeed")
async def get_autofeed(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "threshold": user["autofeed_threshold"],
        "max_coins": user["autofeed_max_coins"],
        "enabled": user["autofeed_threshold"] is not None,
    }


class AutofeedBody(BaseModel):
    threshold: int | None = None
    max_coins: int | None = None


@router.post("/autofeed")
async def set_autofeed(body: AutofeedBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.threshold is None and body.max_coins is None:
        db.set_autofeed(uid, None, None)
        return {"enabled": False, "message": "Auto-feed disabled."}

    if body.threshold is None or not 1 <= body.threshold <= 100:
        raise HTTPException(status_code=400, detail="threshold must be 1–100")
    if body.max_coins is None or body.max_coins <= 0:
        raise HTTPException(status_code=400, detail="max_coins must be > 0")

    db.set_autofeed(uid, body.threshold, body.max_coins)
    return {
        "enabled": True,
        "threshold": body.threshold,
        "max_coins": body.max_coins,
        "message": f"Auto-feed on — feeds below {body.threshold} hunger, up to {body.max_coins} 🪙/tick.",
    }
