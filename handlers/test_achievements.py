import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.achievements import achievements_command
from achievements import check_achievements
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_user(**kwargs):
    defaults = {"user_id": 1, "username": "tester", "group_chat_id": None, "coins": 100}
    defaults.update(kwargs)
    return make_row(**defaults)


@pytest.mark.asyncio
async def test_achievements_unregistered_user():
    update = _make_update()
    with patch("handlers.achievements.db.get_user", return_value=None):
        await achievements_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "start" in reply.lower()


@pytest.mark.asyncio
async def test_achievements_none_earned():
    update = _make_update()
    with patch("handlers.achievements.db.get_user", return_value=_make_user()), patch(
        "handlers.achievements.db.get_achievement_keys", return_value=set()
    ):
        await achievements_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "0/" in reply
    assert "None yet" in reply


@pytest.mark.asyncio
async def test_achievements_some_earned():
    update = _make_update()
    from achievements import ACHIEVEMENTS

    first_key = next(iter(ACHIEVEMENTS))
    with patch("handlers.achievements.db.get_user", return_value=_make_user()), patch(
        "handlers.achievements.db.get_achievement_keys", return_value={first_key}
    ):
        await achievements_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "1/" in reply


@pytest.mark.asyncio
async def test_achievements_shows_locked_entries():
    update = _make_update()
    with patch("handlers.achievements.db.get_user", return_value=_make_user()), patch(
        "handlers.achievements.db.get_achievement_keys", return_value=set()
    ):
        await achievements_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "🔒" in reply


@pytest.mark.asyncio
async def test_check_achievements_uses_row_key_access():
    """Regression: check_achievements must not call .get() on the sqlite3.Row user object."""
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    user = _make_user(username="tester", group_chat_id=-100)

    with patch("achievements.db.get_user", return_value=user), patch(
        "achievements.db.get_achievement_keys", return_value=set()
    ), patch("achievements.db.award_achievement"), patch(
        "achievements.ACHIEVEMENTS",
        {
            "test_ach": {
                "trigger": "checkin",
                "check": lambda uid, u: True,
                "name": "Test",
                "emoji": "🏆",
                "desc": "Test achievement",
            }
        },
    ):
        # This would raise AttributeError if user.get() is called on a FakeRow
        await check_achievements(1, "checkin", ctx)

    ctx.bot.send_message.assert_called_once()
