import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.daily import daily_command, DAILY_COINS, DAILY_COOLDOWN_HOURS


def _make_conn_mock(last_claimed=None):
    inner = MagicMock()
    row = MagicMock()
    row.__getitem__ = MagicMock(side_effect=lambda k: last_claimed if k == "claimed_at" else None)
    inner.execute.return_value.fetchone.return_value = row if last_claimed else None
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_daily_rejects_group_chat():
    update = MagicMock()
    update.effective_chat.type = "group"
    update.message.reply_text = AsyncMock()

    await daily_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "private" in reply.lower()


@pytest.mark.asyncio
async def test_daily_rejects_unknown_user():
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.daily.db.get_user", return_value=None), \
         patch("handlers.daily.db.get_conn", return_value=_make_conn_mock()):
        await daily_command(update, MagicMock())

    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_daily_cooldown_blocks_early_claim():
    recent = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
    cm = _make_conn_mock(last_claimed=recent)

    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.daily.db.get_user", return_value={"coins": 100}), \
         patch("handlers.daily.db.get_conn", return_value=cm):
        await daily_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "h" in reply and ("available" in reply or "Daily" in reply or "⏳" in reply)


@pytest.mark.asyncio
async def test_daily_grants_coins_on_first_claim():
    cm = _make_conn_mock(last_claimed=None)

    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    after_coins = {"coins": 100 + DAILY_COINS}

    with patch("handlers.daily.db.get_user", side_effect=[{"coins": 100}, after_coins]), \
         patch("handlers.daily.db.get_conn", return_value=cm):
        await daily_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert str(DAILY_COINS) in reply
    assert "Daily" in reply or "🎁" in reply


@pytest.mark.asyncio
async def test_daily_grants_coins_after_cooldown_expires():
    old = (datetime.datetime.utcnow() - datetime.timedelta(hours=DAILY_COOLDOWN_HOURS + 1)).isoformat()
    cm = _make_conn_mock(last_claimed=old)

    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    after_coins = {"coins": 200 + DAILY_COINS}

    with patch("handlers.daily.db.get_user", side_effect=[{"coins": 200}, after_coins]), \
         patch("handlers.daily.db.get_conn", return_value=cm):
        await daily_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert str(DAILY_COINS) in reply


def test_daily_constants():
    assert DAILY_COINS == 50
    assert DAILY_COOLDOWN_HOURS == 24
