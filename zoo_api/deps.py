"""Shared FastAPI dependencies."""

import os
from fastapi import HTTPException, Request

from auth import validate_init_data, validate_web_token

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DEV_USER_ID = os.getenv("DEV_USER_ID", "")  # set locally to bypass Telegram auth


async def get_uid(request: Request) -> int:
    if DEV_USER_ID:
        return int(DEV_USER_ID)
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if init_data:
        user_data = validate_init_data(init_data, BOT_TOKEN)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid Telegram auth")
        return int(user_data["id"])
    web_token = request.headers.get("X-Web-Auth-Token", "")
    if web_token:
        uid = validate_web_token(web_token, BOT_TOKEN)
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid or expired web token")
        return uid
    raise HTTPException(status_code=401, detail="Missing Telegram auth")


class _NullBot:
    async def send_message(self, *args, **kwargs):
        pass


class _NullCtx:
    """Minimal ctx stub for check_achievements — awards achievement to DB but skips Telegram notify."""

    bot = _NullBot()


NULL_CTX = _NullCtx()
