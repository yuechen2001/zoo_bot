import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote


def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """Validate Telegram WebApp initData and return the user dict, or None if invalid."""
    try:
        parsed = dict(parse_qs(unquote(init_data), keep_blank_values=True))
        hash_val = parsed.pop("hash", [None])[0]
        if not hash_val:
            return None
        data_check = "\n".join(sorted(f"{k}={v[0]}" for k, v in parsed.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, hash_val):
            return None
        user_str = parsed.get("user", [None])[0]
        if not user_str:
            return None
        return json.loads(user_str)
    except Exception:
        return None


def generate_web_token(user_id: int, bot_token: str) -> str:
    payload = f"{user_id}:{int(time.time())}"
    sig = hmac.new(bot_token.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def validate_web_token(token: str, bot_token: str) -> int | None:
    from game.constants import WEB_LINK_EXPIRY_HOURS

    try:
        user_id_str, timestamp_str, sig = token.split(":", 2)
        payload = f"{user_id_str}:{timestamp_str}"
        expected = hmac.new(
            bot_token.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if int(time.time()) - int(timestamp_str) > WEB_LINK_EXPIRY_HOURS * 3600:
            return None
        return int(user_id_str)
    except Exception:
        return None
