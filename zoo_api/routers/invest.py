import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from config import INVESTMENT_HOURS, INVESTMENT_RETURN_RATE
from game.constants import MIN_INVEST
from game.achievements import check_achievements
from deps import get_uid, NULL_CTX

router = APIRouter(tags=["investments"])


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _ready_at(inv):
    return datetime.datetime.fromisoformat(inv["invested_at"]) + datetime.timedelta(
        hours=INVESTMENT_HOURS
    )


def _is_ready(inv) -> bool:
    return _now() >= _ready_at(inv)


def _seconds_remaining(inv) -> int:
    remaining = _ready_at(inv) - _now()
    return max(0, int(remaining.total_seconds()))


@router.get("/investments")
async def get_investment(uid: int = Depends(get_uid)):
    inv = db.get_active_investment(uid)
    if not inv:
        return {
            "active": False,
            "rate_pct": int(INVESTMENT_RETURN_RATE * 100),
            "hours": INVESTMENT_HOURS,
        }
    return {
        "active": True,
        "id": inv["id"],
        "amount": inv["amount"],
        "return_amount": inv["return_amount"],
        "rate_pct": int(INVESTMENT_RETURN_RATE * 100),
        "hours": INVESTMENT_HOURS,
        "is_ready": _is_ready(inv),
        "seconds_remaining": _seconds_remaining(inv),
    }


class InvestBody(BaseModel):
    amount: int


@router.post("/investments/create")
async def create_investment(body: InvestBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.amount < MIN_INVEST:
        raise HTTPException(
            status_code=400, detail=f"Minimum investment is {MIN_INVEST} 🪙"
        )

    if user["coins"] < body.amount:
        raise HTTPException(status_code=400, detail="Not enough coins")

    if db.get_active_investment(uid):
        raise HTTPException(status_code=400, detail="Already have an active investment")

    return_amount = round(body.amount * (1 + INVESTMENT_RETURN_RATE))
    db.create_investment(uid, body.amount, return_amount)
    db.add_coins(uid, -body.amount)

    return {
        "amount": body.amount,
        "return_amount": return_amount,
        "rate_pct": int(INVESTMENT_RETURN_RATE * 100),
        "hours": INVESTMENT_HOURS,
    }


@router.post("/investments/collect")
async def collect_investment(uid: int = Depends(get_uid)):
    inv = db.get_active_investment(uid)
    if not inv:
        raise HTTPException(status_code=400, detail="No active investment")

    if not _is_ready(inv):
        secs = _seconds_remaining(inv)
        h, rem = divmod(secs, 3600)
        m = rem // 60
        detail = (
            f"Not ready yet! {h}h {m}m remaining"
            if h
            else f"Not ready yet! {m}m remaining"
        )
        raise HTTPException(status_code=400, detail=detail)

    db.collect_investment(inv["id"])
    db.add_coins(uid, inv["return_amount"])
    profit = inv["return_amount"] - inv["amount"]
    await check_achievements(uid, "investment", NULL_CTX)
    return {"return_amount": inv["return_amount"], "profit": profit}
