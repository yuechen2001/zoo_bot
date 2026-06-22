import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add zoo_cli to path so db, game.*, config all import cleanly
ZOO_BOT_PATH = os.getenv("ZOO_BOT_PATH", str(Path(__file__).parent.parent / "zoo_cli"))
sys.path.insert(0, ZOO_BOT_PATH)

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from deps import get_uid  # noqa: E402
from routers import achievements, animals, breed, catch, enclosures, inventory, invest, minigames, quests, store, user  # noqa: E402

WEBAPP_ORIGIN = os.getenv("WEBAPP_ORIGIN", "*")

app = FastAPI(title="Zoo Bot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEBAPP_ORIGIN] if WEBAPP_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routers share the same auth dependency (supports DEV_USER_ID for local dev)
_auth = [Depends(get_uid)]
app.include_router(user.router, prefix="/api/v1", dependencies=_auth)
app.include_router(animals.router, prefix="/api/v1", dependencies=_auth)
app.include_router(catch.router, prefix="/api/v1", dependencies=_auth)
app.include_router(breed.router, prefix="/api/v1", dependencies=_auth)
app.include_router(enclosures.router, prefix="/api/v1", dependencies=_auth)
app.include_router(store.router, prefix="/api/v1", dependencies=_auth)
app.include_router(inventory.router, prefix="/api/v1", dependencies=_auth)
app.include_router(quests.router, prefix="/api/v1", dependencies=_auth)
app.include_router(achievements.router, prefix="/api/v1", dependencies=_auth)
app.include_router(minigames.router, prefix="/api/v1", dependencies=_auth)
app.include_router(invest.router, prefix="/api/v1", dependencies=_auth)


@app.get("/health")
async def health():
    return {"status": "ok"}
