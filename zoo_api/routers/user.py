from fastapi import APIRouter, Depends, HTTPException

import db
from deps import get_uid

router = APIRouter(tags=["user"])


def _row_to_dict(row) -> dict:
    return dict(row) if row else {}


@router.get("/user/me")
async def get_me(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found — use /start first")
    active_breed = db.get_active_breed(uid)
    pending_coins = db.get_pending_enclosure_coins(uid)
    return {
        **_row_to_dict(user),
        "active_breed": _row_to_dict(active_breed) if active_breed else None,
        "pending_enclosure_coins": pending_coins,
    }
