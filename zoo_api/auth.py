import hashlib
import hmac
import json
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
