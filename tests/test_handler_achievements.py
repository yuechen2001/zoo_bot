import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.achievements import achievements_command


def _make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


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
    with patch("handlers.achievements.db.get_user", return_value={"user_id": 1}), patch(
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
    with patch("handlers.achievements.db.get_user", return_value={"user_id": 1}), patch(
        "handlers.achievements.db.get_achievement_keys", return_value={first_key}
    ):
        await achievements_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "1/" in reply


@pytest.mark.asyncio
async def test_achievements_shows_locked_entries():
    update = _make_update()
    with patch("handlers.achievements.db.get_user", return_value={"user_id": 1}), patch(
        "handlers.achievements.db.get_achievement_keys", return_value=set()
    ):
        await achievements_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "🔒" in reply
