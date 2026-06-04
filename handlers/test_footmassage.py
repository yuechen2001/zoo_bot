import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from conftest import make_row
from handlers.footmassage import footmassage_command, MASSAGE_COST


def _make_update():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    return update, MagicMock(user_data={})


def _make_user(**kw):
    defaults = {"user_id": 1, "coins": 200, "massage_active_until": None}
    return make_row(**{**defaults, **kw})


def _future(minutes=30):
    return (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(minutes=minutes)
    ).isoformat()


def _past(hours=1):
    return (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=hours)
    ).isoformat()


def _conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, inner


@pytest.mark.asyncio
async def test_no_user():
    update, ctx = _make_update()
    with patch("handlers.footmassage.db.get_user", return_value=None):
        await footmassage_command(update, ctx)
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_happy_path_activates_massage():
    update, ctx = _make_update()
    cm, inner = _conn_mock()
    with patch("handlers.footmassage.db.get_user", return_value=_make_user()), patch(
        "handlers.footmassage.db.get_conn", return_value=cm
    ):
        await footmassage_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "massage" in reply.lower()
    inner.execute.assert_called_once()
    _sql, params = inner.execute.call_args[0]
    assert MASSAGE_COST in params


@pytest.mark.asyncio
async def test_insufficient_coins():
    update, ctx = _make_update()
    with patch("handlers.footmassage.db.get_user", return_value=_make_user(coins=10)):
        await footmassage_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "coins" in reply.lower() or "enough" in reply.lower()


@pytest.mark.asyncio
async def test_already_active_shows_remaining_time():
    update, ctx = _make_update()
    with patch(
        "handlers.footmassage.db.get_user",
        return_value=_make_user(massage_active_until=_future(30)),
    ):
        await footmassage_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "relaxed" in reply.lower() or "left" in reply.lower()


@pytest.mark.asyncio
async def test_cooldown_blocks_repurchase():
    update, ctx = _make_update()
    # expired 1h ago — still within the 4h cooldown window
    with patch(
        "handlers.footmassage.db.get_user",
        return_value=_make_user(massage_active_until=_past(1)),
    ):
        await footmassage_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert any(w in reply.lower() for w in ("break", "try again", "wait", "available"))
