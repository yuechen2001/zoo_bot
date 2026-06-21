from fastapi import APIRouter, Depends, HTTPException

import db
from game.achievements import ACHIEVEMENTS
from deps import get_uid

router = APIRouter(tags=["achievements"])


@router.get("/achievements")
async def get_achievements(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    earned_keys = db.get_achievement_keys(uid)
    return {
        "earned": list(earned_keys),
        "all": {
            key: {
                "emoji": ach["emoji"],
                "name": ach["name"],
                "desc": ach["desc"],
                "trigger": ach["trigger"],
                "earned": key in earned_keys,
            }
            for key, ach in ACHIEVEMENTS.items()
        },
    }
