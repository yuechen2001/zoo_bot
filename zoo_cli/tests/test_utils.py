import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from utils import replace_command_ui, format_mention


# ── format_mention ────────────────────────────────────────────────────────────


def test_format_mention_with_username():
    assert format_mention("alice") == "@alice"


def test_format_mention_with_user_id_no_username():
    assert format_mention(None, 42) == "user 42"


def test_format_mention_no_username_no_id():
    assert format_mention(None, None) == "someone"


def test_format_mention_empty_username_falls_back_to_id():
    assert format_mention("", 7) == "user 7"


# ── replace_command_ui ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replace_command_ui_stores_new_entry():
    ctx = MagicMock()
    ctx.user_data = {}
    update = MagicMock()
    update.effective_chat.id = 10
    update.message.message_id = 99
    bot_msg = MagicMock()
    bot_msg.message_id = 200

    await replace_command_ui(ctx, "my_ui", update, bot_msg)

    assert ctx.user_data["my_ui"] == (10, 200, 99)


@pytest.mark.asyncio
async def test_replace_command_ui_deletes_previous_messages():
    ctx = MagicMock()
    ctx.user_data = {"my_ui": (10, 111, 222)}
    ctx.bot.delete_message = AsyncMock()
    update = MagicMock()
    update.effective_chat.id = 10
    update.message.message_id = 300
    bot_msg = MagicMock()
    bot_msg.message_id = 400

    with patch("utils.asyncio.create_task") as mock_task:
        await replace_command_ui(ctx, "my_ui", update, bot_msg)

    assert mock_task.call_count == 2
    assert ctx.user_data["my_ui"] == (10, 400, 300)
