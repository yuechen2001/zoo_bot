def format_mention(username: str | None, user_id: int | None = None) -> str:
    """Format a user reference for Telegram messages.

    Returns @username if available, falls back to 'user {id}', then 'someone'.
    """
    if username:
        return f"@{username}"
    if user_id:
        return f"user {user_id}"
    return "someone"
