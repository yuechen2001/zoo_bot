import asyncio
import logging
from telegram.error import BadRequest

logger = logging.getLogger(__name__)


async def _delete_silently(bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except BadRequest:
        pass
    except Exception:
        logger.warning("Failed to delete message %s in chat %s", message_id, chat_id, exc_info=True)


async def replace_command_ui(ctx, key: str, update, bot_msg) -> None:
    """On each invocation: fire-and-forget delete the previous bot response and the
    previous command message, then store the current pair for the next invocation."""
    old = ctx.user_data.pop(key, None)
    if old:
        chat_id, old_bot_id, old_cmd_id = old
        asyncio.create_task(_delete_silently(ctx.bot, chat_id, old_bot_id))
        asyncio.create_task(_delete_silently(ctx.bot, chat_id, old_cmd_id))
    ctx.user_data[key] = (update.effective_chat.id, bot_msg.message_id, update.message.message_id)


def format_mention(username: str | None, user_id: int | None = None) -> str:
    """Format a user reference for Telegram messages.

    Returns @username if available, falls back to 'user {id}', then 'someone'.
    """
    if username:
        return f"@{username}"
    if user_id:
        return f"user {user_id}"
    return "someone"
