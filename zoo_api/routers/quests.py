from fastapi import APIRouter, Depends, HTTPException

import db
from game.quests_data import ARCS, CHAPTERS
from deps import get_uid

router = APIRouter(tags=["quests"])


@router.get("/quests")
async def get_quests(uid: int = Depends(get_uid)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    progress_rows = db.get_quest_progress(uid)
    progress_by_chapter = {r["chapter_num"]: dict(r) for r in progress_rows}
    active_chapter = db.get_active_chapter(uid)

    chapters_out = []
    for num, ch in CHAPTERS.items():
        prog = progress_by_chapter.get(num)
        tasks_out = []
        if prog:
            user_row = db.get_user(uid)
            for t in ch["tasks"]:
                tasks_out.append(
                    {
                        "desc": t["desc"],
                        "done": t["check"](uid, user_row),
                    }
                )
        chapters_out.append(
            {
                "chapter_num": num,
                "arc": ch["arc"],
                "title": ch["title"],
                "intro": ch["intro"],
                "outro": ch["outro"],
                "reward_coins": ch["reward_coins"],
                "reward_species": ch["reward_species"],
                "reward_title": ch["reward_title"],
                "tasks": tasks_out,
                "started": prog is not None,
                "completed": prog["completed_at"] is not None if prog else False,
                "is_active": num == active_chapter,
            }
        )

    return {
        "arcs": dict(ARCS),
        "active_chapter": active_chapter,
        "chapters": chapters_out,
    }
