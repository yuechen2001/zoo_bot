import asyncio


async def replace_command_ui(ctx, key: str, update, bot_msg) -> None:
    """Delete the previous bot response for this command, delete the current command
    message, and store the new bot response ID for the next invocation."""
    old = ctx.user_data.pop(key, None)
    if old:
        asyncio.create_task(ctx.bot.delete_message(chat_id=old[0], message_id=old[1]))
    try:
        await update.message.delete()
    except Exception:
        pass
    ctx.user_data[key] = (update.effective_chat.id, bot_msg.message_id)


def format_mention(username: str | None, user_id: int | None = None) -> str:
    """Format a user reference for Telegram messages.

    Returns @username if available, falls back to 'user {id}', then 'someone'.
    """
    if username:
        return f"@{username}"
    if user_id:
        return f"user {user_id}"
    return "someone"
