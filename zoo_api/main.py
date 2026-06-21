import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add zoo_cli to path so db, game.*, config all import cleanly
ZOO_BOT_PATH = os.getenv("ZOO_BOT_PATH", str(Path(__file__).parent.parent / "zoo_cli"))
sys.path.insert(0, ZOO_BOT_PATH)

from fastapi import Depends, FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from auth import validate_init_data  # noqa: E402
from routers import achievements, animals, breed, catch, enclosures, inventory, minigames, quests, store, user  # noqa: E402

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_ORIGIN = os.getenv("WEBAPP_ORIGIN", "*")

app = FastAPI(title="Zoo Bot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEBAPP_ORIGIN] if WEBAPP_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user_id(request: Request) -> int:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram auth")
    user_data = validate_init_data(init_data, BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    return int(user_data["id"])


# Inject user_id dependency into all routers
app.include_router(user.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(animals.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(catch.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(breed.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(enclosures.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(store.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(inventory.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(quests.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(achievements.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])
app.include_router(minigames.router, prefix="/api/v1", dependencies=[Depends(get_current_user_id)])


@app.get("/health")
async def health():
    return {"status": "ok"}
