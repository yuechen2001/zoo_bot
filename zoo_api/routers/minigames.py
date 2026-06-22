import datetime
import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from game.constants import (
    COINS_CORRECT,
    COINS_WRONG,
    DAILY_COOLDOWN_HOURS,
    DAILY_STREAK_EXPIRY_HOURS,
    DAILY_TIERS,
    MASSAGE_COOLDOWN_HOURS,
    MASSAGE_COST,
    MASSAGE_DURATION_HOURS,
    MAX_BET,
    SPIN_COST,
    SYMBOLS,
    TRIVIA_COOLDOWN_MINUTES,
    TRIVIA_WINDOW_MINUTES,
    WIN_2,
    WIN_3,
    TRIVIA_WAGER_OPTIONS,
)
from game.trivia_data import QUESTIONS as TRIVIA_QUESTIONS
from game.achievements import check_achievements
from deps import get_uid, NULL_CTX

router = APIRouter(tags=["minigames"])


# ── Daily ─────────────────────────────────────────────────────────────────────


@router.post("/daily/claim")
async def claim_daily(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    now_str = now.isoformat()
    last = db.get_last_daily_at(uid)

    if last:
        last_dt = datetime.datetime.fromisoformat(last)
        elapsed_h = (now - last_dt).total_seconds() / 3600
        if elapsed_h < DAILY_COOLDOWN_HOURS:
            remaining = DAILY_COOLDOWN_HOURS - elapsed_h
            raise HTTPException(
                status_code=400,
                detail=f"Daily already claimed. Try again in {remaining:.1f}h",
            )
        streak_broken = elapsed_h > DAILY_STREAK_EXPIRY_HOURS
    else:
        streak_broken = False

    new_streak = 0 if streak_broken else (user["daily_streak"] or 0) + 1
    coins = 50
    for threshold, reward in DAILY_TIERS:
        if new_streak >= threshold:
            coins = reward
            break

    db.claim_daily(uid, coins, new_streak, now_str)
    await check_achievements(uid, "daily", NULL_CTX)
    return {"coins": coins, "streak": new_streak}


# ── Trivia ─────────────────────────────────────────────────────────────────────


@router.get("/trivia/question")
async def get_trivia_question(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    last = db.get_last_trivia_at(uid)
    if last:
        elapsed_m = (now - datetime.datetime.fromisoformat(last)).total_seconds() / 60
        if elapsed_m < TRIVIA_COOLDOWN_MINUTES:
            remaining = TRIVIA_COOLDOWN_MINUTES - elapsed_m
            raise HTTPException(
                status_code=400,
                detail=f"Trivia on cooldown. Try again in {remaining:.0f}m",
            )

    q = random.choice(TRIVIA_QUESTIONS)
    now_str = now.isoformat()
    db.record_trivia(uid, now_str)
    return {
        "question": q["q"],
        "choices": q["options"],
        "wager_options": TRIVIA_WAGER_OPTIONS,
        "expires_at": (now + datetime.timedelta(minutes=TRIVIA_WINDOW_MINUTES)).isoformat(),
        "_answer_key": q["answer"],
    }


class TriviaAnswerBody(BaseModel):
    question: str
    answer: str
    wager: int = 0


@router.post("/trivia/answer")
async def answer_trivia(body: TriviaAnswerBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = next((q for q in TRIVIA_QUESTIONS if q["q"] == body.question), None)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    correct = body.answer == q["answer"]
    wager = body.wager if body.wager in TRIVIA_WAGER_OPTIONS else 0

    if correct:
        coins = COINS_CORRECT + wager * 2
    else:
        coins = -(COINS_WRONG + wager)
        coins = max(-user["coins"], coins)

    db.add_coins(uid, coins)
    await check_achievements(uid, "trivia", NULL_CTX)
    return {"correct": correct, "answer": q["answer"], "coins": coins}


# ── Gamble ─────────────────────────────────────────────────────────────────────


class GambleBody(BaseModel):
    bet: int


@router.post("/gamble")
async def gamble(body: GambleBody, uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    bet = max(1, min(body.bet, MAX_BET))
    if user["coins"] < bet:
        raise HTTPException(status_code=400, detail="Not enough coins")
    won = random.random() < 0.5
    delta = bet if won else -bet
    db.add_coins(uid, delta)
    return {"won": won, "bet": bet, "delta": delta}


# ── Slots ─────────────────────────────────────────────────────────────────────


@router.post("/slots/spin")
async def slots_spin(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["coins"] < SPIN_COST:
        raise HTTPException(status_code=400, detail=f"Need {SPIN_COST} coins to spin")

    db.deduct_coins(uid, SPIN_COST)
    reels = [random.choice(SYMBOLS) for _ in range(3)]
    if reels[0] == reels[1] == reels[2]:
        payout = WIN_3
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        payout = WIN_2
    else:
        payout = 0

    if payout:
        db.add_coins(uid, payout)

    return {"reels": reels, "payout": payout, "net": payout - SPIN_COST}


# ── Foot Massage ──────────────────────────────────────────────────────────────


@router.post("/minigames/massage")
async def foot_massage(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    active_until = user["massage_active_until"]
    if active_until:
        au_dt = datetime.datetime.fromisoformat(active_until)
        if now < au_dt:
            remaining = int((au_dt - now).total_seconds())
            raise HTTPException(status_code=400, detail=f"Massage active! {remaining // 60}m remaining")
        cooldown_end = au_dt + datetime.timedelta(hours=MASSAGE_COOLDOWN_HOURS)
        if now < cooldown_end:
            remaining = int((cooldown_end - now).total_seconds())
            raise HTTPException(status_code=400, detail=f"On cooldown. {remaining // 60}m remaining")

    if user["coins"] < MASSAGE_COST:
        raise HTTPException(status_code=400, detail=f"Need {MASSAGE_COST} 🪙 for a massage")

    massage_until = (now + datetime.timedelta(hours=MASSAGE_DURATION_HOURS)).isoformat()
    db.activate_massage(uid, MASSAGE_COST, massage_until)
    return {"cost": MASSAGE_COST, "active_until": massage_until}
