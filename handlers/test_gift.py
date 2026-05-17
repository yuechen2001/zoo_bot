import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.gift import gift_command
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _make_update(args=None):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    update.message.bot = MagicMock()
    update.message.bot.send_message = AsyncMock()
    ctx = MagicMock()
    ctx.args = args or []
    return update, ctx


def _make_sender(**kw):
    defaults = {"user_id": 1, "username": "alice", "group_chat_id": -100, "coins": 200}
    return make_row(**{**defaults, **kw})


def _make_recipient(**kw):
    defaults = {"user_id": 2, "username": "bob", "group_chat_id": -100, "coins": 50}
    return make_row(**{**defaults, **kw})


def _make_animal(**kw):
    defaults = {
        "animal_id": "a1",
        "species_name": "Mouse",
        "emoji": "🐭",
        "rarity": "common",
        "habitat": "woodland",
        "is_breeding": 0,
        "nickname": None,
        "catch_cost": 20,
    }
    return make_row(**{**defaults, **kw})


@pytest.fixture(autouse=True)
def no_achievements(monkeypatch):
    monkeypatch.setattr("handlers.gift.db.transfer_animal", MagicMock())


@pytest.mark.asyncio
async def test_gift_shows_usage_with_no_args():
    update, ctx = _make_update(args=[])
    with patch("handlers.gift.db.get_user", return_value=_make_sender()):
        await gift_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "/gift" in reply


@pytest.mark.asyncio
async def test_gift_unknown_recipient():
    update, ctx = _make_update(args=["1", "@ghost"])
    with patch("handlers.gift.db.get_user", return_value=_make_sender()), patch(
        "handlers.gift.db.get_user_by_username", return_value=None
    ):
        await gift_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "started" in reply.lower() or "not found" in reply.lower()


@pytest.mark.asyncio
async def test_gift_blocks_breeding_animal():
    update, ctx = _make_update(args=["1", "@bob"])
    animal = _make_animal(is_breeding=1)
    with patch("handlers.gift.db.get_user", return_value=_make_sender()), patch(
        "handlers.gift.db.get_user_by_username", return_value=_make_recipient()
    ), patch("handlers.gift.db.get_animal_by_position", return_value=animal):
        await gift_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "breeding" in reply.lower()


@pytest.mark.asyncio
async def test_gift_blocks_full_enclosure():
    update, ctx = _make_update(args=["1", "@bob"])
    animal = _make_animal()
    with patch("handlers.gift.db.get_user", return_value=_make_sender()), patch(
        "handlers.gift.db.get_user_by_username", return_value=_make_recipient()
    ), patch("handlers.gift.db.get_animal_by_position", return_value=animal), patch(
        "handlers.gift.db.has_pending_trade_for_animal", return_value=False
    ), patch(
        "handlers.gift.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.gift.db.get_animal_count_by_habitat", return_value=3
    ):
        await gift_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "full" in reply.lower()


@pytest.mark.asyncio
async def test_gift_successful_transfer():
    update, ctx = _make_update(args=["1", "@bob"])
    animal = _make_animal()
    with patch("handlers.gift.db.get_user", return_value=_make_sender()), patch(
        "handlers.gift.db.get_user_by_username", return_value=_make_recipient()
    ), patch("handlers.gift.db.get_animal_by_position", return_value=animal), patch(
        "handlers.gift.db.has_pending_trade_for_animal", return_value=False
    ), patch(
        "handlers.gift.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.gift.db.get_animal_count_by_habitat", return_value=1
    ), patch(
        "handlers.gift.db.transfer_animal"
    ) as mock_transfer:
        await gift_command(update, ctx)
    mock_transfer.assert_called_once_with("a1", 2)
    update.message.bot.send_message.assert_called_once()
    msg = update.message.bot.send_message.call_args[0][1]
    assert "gifted" in msg.lower() or "🎁" in msg
