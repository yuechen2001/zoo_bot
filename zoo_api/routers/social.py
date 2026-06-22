import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from config import TRADE_EXPIRY_MINUTES
from game.constants import FEED_COST_BY_RARITY, FEED_HUNGER, VISIT_FEED_BONUS, VISIT_FEED_COOLDOWN_HOURS
from game.species_data import ENCLOSURE_LEVELS
from deps import get_uid

router = APIRouter(tags=["social"])


def _get_partner(uid: int):
    user = db.get_user(uid)
    if not user or not user["group_chat_id"]:
        return None, None
    others = db.get_users_in_group(user["group_chat_id"])
    partner = next((u for u in others if u["user_id"] != uid), None)
    return user, partner


@router.get("/social/partner")
async def get_partner(uid: int = Depends(get_uid)):
    _, partner = _get_partner(uid)
    if not partner:
        return None
    animals = db.get_animals(partner["user_id"])
    return {
        "user_id": partner["user_id"],
        "username": partner["username"] or f"user_{partner['user_id']}",
        "coins": partner["coins"],
        "animal_count": len(animals),
        "animals": [dict(a) for a in animals],
    }


@router.post("/social/partner/feed")
async def visit_feed(uid: int = Depends(get_uid)):
    user, partner = _get_partner(uid)
    if not partner:
        raise HTTPException(status_code=404, detail="No partner found in your group")

    last = db.get_last_visit_feed(uid, partner["user_id"])
    if last:
        last_at = datetime.datetime.fromisoformat(last["fed_at"])
        elapsed = (datetime.datetime.utcnow() - last_at).total_seconds()
        if elapsed < VISIT_FEED_COOLDOWN_HOURS * 3600:
            remaining = int(VISIT_FEED_COOLDOWN_HOURS * 3600 - elapsed)
            h, m = divmod(remaining // 60, 60)
            raise HTTPException(status_code=400, detail=f"Cooldown: {h}h {m}m remaining")

    animals = db.get_animals(partner["user_id"])
    hungry = [a for a in animals if a["hunger"] < 100]
    if not hungry:
        raise HTTPException(status_code=400, detail="All animals are fully fed!")

    target = min(hungry, key=lambda a: a["hunger"])
    cost = FEED_COST_BY_RARITY.get(target["rarity"], 5)
    if user["coins"] < cost:
        raise HTTPException(status_code=400, detail=f"Not enough coins (need {cost} 🪙)")

    new_hunger = min(100, target["hunger"] + FEED_HUNGER)
    now = datetime.datetime.utcnow().isoformat()
    db.feed_animal(uid, target["animal_id"], new_hunger, cost)
    db.add_coins(uid, VISIT_FEED_BONUS)
    db.record_visit_feed(uid, partner["user_id"], now)

    name = target["nickname"] or target["species_name"]
    return {
        "success": True,
        "message": f"Fed {target['emoji']} {name}! -{cost} 🪙, +{VISIT_FEED_BONUS} 🪙 bonus",
        "coins_spent": cost,
        "coins_earned": VISIT_FEED_BONUS,
    }


class GiftBody(BaseModel):
    animal_id: str


@router.post("/social/gift")
async def gift_animal(body: GiftBody, uid: int = Depends(get_uid)):
    _, partner = _get_partner(uid)
    if not partner:
        raise HTTPException(status_code=404, detail="No partner found in your group")

    animal = db.get_animal(body.animal_id)
    if not animal or animal["user_id"] != uid:
        raise HTTPException(status_code=404, detail="Animal not found")
    if animal["is_breeding"]:
        raise HTTPException(status_code=400, detail="Animal is currently breeding")
    if db.has_pending_trade_for_animal(body.animal_id):
        raise HTTPException(status_code=400, detail="Animal has a pending trade — cancel it first")

    habitat = animal["habitat"]
    enc_level = db.get_enclosure_level(partner["user_id"], habitat)
    capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
    current = db.get_animal_count_by_habitat(partner["user_id"], habitat)
    if current >= capacity:
        raise HTTPException(status_code=400, detail=f"Partner's {habitat} enclosure is full")

    db.transfer_animal(body.animal_id, partner["user_id"])
    name = animal["nickname"] or animal["species_name"]
    return {"success": True, "message": f"🎁 {animal['emoji']} {name} gifted to @{partner['username']}!"}


@router.get("/social/trades")
async def list_trades(uid: int = Depends(get_uid)):
    _, partner = _get_partner(uid)
    partner_id = partner["user_id"] if partner else None

    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM trades WHERE status = 'pending' "
            "AND (proposer_id = ? OR recipient_id = ?) ORDER BY created_at DESC",
            (uid, uid),
        ).fetchall()

    result = []
    for row in rows:
        my_animal_id = row["proposer_animal_id"] if row["proposer_id"] == uid else row["recipient_animal_id"]
        their_animal_id = row["recipient_animal_id"] if row["proposer_id"] == uid else row["proposer_animal_id"]
        my_animal = db.get_animal(my_animal_id)
        their_animal = db.get_animal(their_animal_id)
        result.append({
            "trade_id": row["id"],
            "is_incoming": row["recipient_id"] == uid,
            "my_animal": dict(my_animal) if my_animal else None,
            "their_animal": dict(their_animal) if their_animal else None,
            "created_at": row["created_at"],
        })
    return {"trades": result, "partner_id": partner_id}


class ProposeTradeBody(BaseModel):
    my_animal_id: str
    their_animal_id: str


@router.post("/social/trades")
async def propose_trade(body: ProposeTradeBody, uid: int = Depends(get_uid)):
    _, partner = _get_partner(uid)
    if not partner:
        raise HTTPException(status_code=404, detail="No partner found in your group")

    my_animal = db.get_animal(body.my_animal_id)
    if not my_animal or my_animal["user_id"] != uid:
        raise HTTPException(status_code=404, detail="Your animal not found")
    their_animal = db.get_animal(body.their_animal_id)
    if not their_animal or their_animal["user_id"] != partner["user_id"]:
        raise HTTPException(status_code=404, detail="Partner's animal not found")

    if my_animal["is_breeding"]:
        raise HTTPException(status_code=400, detail="Your animal is breeding")
    if their_animal["is_breeding"]:
        raise HTTPException(status_code=400, detail="Their animal is breeding")
    if db.has_pending_trade_for_animal(body.my_animal_id):
        raise HTTPException(status_code=400, detail="Your animal already has a pending trade")
    if db.has_pending_trade_for_animal(body.their_animal_id):
        raise HTTPException(status_code=400, detail="Their animal already has a pending trade")

    trade_id = db.create_trade(uid, partner["user_id"], body.my_animal_id, body.their_animal_id)
    my_name = my_animal["nickname"] or my_animal["species_name"]
    their_name = their_animal["nickname"] or their_animal["species_name"]
    return {
        "trade_id": trade_id,
        "message": f"🔄 Trade proposed: {my_animal['emoji']} {my_name} ↔ {their_animal['emoji']} {their_name}. Awaiting response.",
    }


class TradeRespondBody(BaseModel):
    action: str  # "accept" | "decline"


@router.post("/social/trades/{trade_id}/respond")
async def respond_trade(trade_id: int, body: TradeRespondBody, uid: int = Depends(get_uid)):
    trade = db.get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade["recipient_id"] != uid:
        raise HTTPException(status_code=403, detail="Not your trade to respond to")
    if trade["status"] != "pending":
        raise HTTPException(status_code=400, detail="Trade is no longer pending")

    created = datetime.datetime.fromisoformat(trade["created_at"])
    elapsed_min = (datetime.datetime.utcnow() - created).total_seconds() / 60
    if elapsed_min > TRADE_EXPIRY_MINUTES:
        db.resolve_trade(trade_id, "declined")
        raise HTTPException(status_code=400, detail="Trade has expired")

    if body.action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="action must be accept or decline")

    if body.action == "accept":
        p_animal = db.get_animal(trade["proposer_animal_id"])
        r_animal = db.get_animal(trade["recipient_animal_id"])
        p_habitat = p_animal["habitat"]
        r_habitat = r_animal["habitat"]
        proposer_id = trade["proposer_id"]

        if p_habitat != r_habitat:
            used = db.get_animal_count_by_habitat(proposer_id, r_habitat)
            cap = ENCLOSURE_LEVELS[db.get_enclosure_level(proposer_id, r_habitat)]["capacity"]
            if used >= cap:
                raise HTTPException(status_code=400, detail="Proposer's enclosure is full for that habitat")
            used = db.get_animal_count_by_habitat(uid, p_habitat)
            cap = ENCLOSURE_LEVELS[db.get_enclosure_level(uid, p_habitat)]["capacity"]
            if used >= cap:
                raise HTTPException(status_code=400, detail="Your enclosure is full for that habitat")

        db.resolve_trade(trade_id, "accepted")
        p_name = p_animal["nickname"] or p_animal["species_name"]
        r_name = r_animal["nickname"] or r_animal["species_name"]
        return {"success": True, "message": f"✅ Trade complete! {p_animal['emoji']} {p_name} ↔ {r_animal['emoji']} {r_name}"}
    else:
        db.resolve_trade(trade_id, "declined")
        return {"success": True, "message": "Trade declined."}
