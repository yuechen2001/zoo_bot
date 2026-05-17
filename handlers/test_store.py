import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.store import store_command
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _make_update(args=None):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args or []
    return update, ctx


def _make_user(**kw):
    defaults = {
        "user_id": 1,
        "username": "alice",
        "group_chat_id": -100,
        "coins": 500,
        "lucky_catch_active": 0,
        "active_title": None,
    }
    return make_row(**{**defaults, **kw})


@pytest.mark.asyncio
async def test_store_shows_items():
    update, ctx = _make_update(args=[])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Mega Feed" in reply
    assert "Lucky Token" in reply
    assert "Zookeeper" in reply


@pytest.mark.asyncio
async def test_store_buy_insufficient_coins():
    update, ctx = _make_update(args=["buy", "mega_feed"])
    with patch("handlers.store.db.get_user", return_value=_make_user(coins=5)):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "not enough" in reply.lower() or "coins" in reply.lower()


@pytest.mark.asyncio
async def test_store_buy_unknown_item():
    update, ctx = _make_update(args=["buy", "dragon_egg"])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "unknown" in reply.lower() or "dragon_egg" in reply.lower()


@pytest.mark.asyncio
async def test_store_buy_lucky_token_sets_flag():
    update, ctx = _make_update(args=["buy", "lucky_token"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_conn"
    ) as mock_conn, patch("handlers.store.db.set_lucky_catch") as mock_set:
        inner = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=inner)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        await store_command(update, ctx)
    mock_set.assert_called_once_with(1, True)
    reply = update.message.reply_text.call_args[0][0]
    assert "Lucky Token" in reply


@pytest.mark.asyncio
async def test_store_buy_cosmetic_records_purchase():
    update, ctx = _make_update(args=["buy", "title_keeper"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=False
    ), patch("handlers.store.db.get_conn") as mock_conn, patch(
        "handlers.store.db.record_purchase"
    ) as mock_record:
        inner = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=inner)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        await store_command(update, ctx)
    mock_record.assert_called_once_with(1, "title_keeper")
    reply = update.message.reply_text.call_args[0][0]
    assert "Zookeeper" in reply


@pytest.mark.asyncio
async def test_store_equip_title_sets_active():
    update, ctx = _make_update(args=["equip", "title_keeper"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=True
    ), patch("handlers.store.db.set_active_title") as mock_set:
        await store_command(update, ctx)
    mock_set.assert_called_once_with(1, "title_keeper")


@pytest.mark.asyncio
async def test_store_equip_unowned_title_blocked():
    update, ctx = _make_update(args=["equip", "title_legend"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=False
    ):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "don't own" in reply.lower() or "buy" in reply.lower()
