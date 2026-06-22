import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add zoo_cli to path so db, game.*, config all import cleanly
ZOO_BOT_PATH = os.getenv("ZOO_BOT_PATH", str(Path(__file__).parent.parent / "zoo_cli"))
sys.path.insert(0, ZOO_BOT_PATH)

from fastapi import Depends, FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from deps import get_uid  # noqa: E402
from routers import achievements, animals, autofeed, breed, catch, directory, enclosures, escapes, inventory, invest, minigames, quests, store, user, wild_events  # noqa: E402

WEBAPP_ORIGIN = os.getenv("WEBAPP_ORIGIN", "*")
API_SECRET = os.getenv("API_SECRET", "")

app = FastAPI(title="Zoo Bot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEBAPP_ORIGIN] if WEBAPP_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    if API_SECRET and request.headers.get("X-Internal-API-Key") != API_SECRET:
        return JSONResponse({"detail": "Forbidden"}, status_code=403)
    return await call_next(request)

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
app.include_router(escapes.router, prefix="/api/v1", dependencies=_auth)
app.include_router(wild_events.router, prefix="/api/v1", dependencies=_auth)
app.include_router(directory.router, prefix="/api/v1", dependencies=_auth)
app.include_router(autofeed.router, prefix="/api/v1", dependencies=_auth)


@app.get("/health")
async def health():
    return {"status": "ok"}
