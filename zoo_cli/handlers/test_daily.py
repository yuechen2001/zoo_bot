import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.daily import daily_command, DAILY_COOLDOWN_HOURS, DAILY_TIERS, _daily_coins


@pytest.fixture(autouse=True)
def no_achievements(monkeypatch):
    monkeypatch.setattr("game.achievements.check_achievements", AsyncMock())


def _make_conn_mock(last_claimed=None):
    inner = MagicMock()
    row = MagicMock()
    row.__getitem__ = MagicMock(side_effect=lambda k: last_claimed if k == "claimed_at" else None)
    inner.execute.return_value.fetchone.return_value = row if last_claimed else None
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _make_user(coins=100, daily_streak=0):
    return {"coins": coins, "daily_streak": daily_streak}


@pytest.mark.asyncio
async def test_daily_rejects_unknown_user():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.daily.db.get_user", return_value=None), patch(
        "handlers.daily.db.get_conn", return_value=_make_conn_mock()
    ):
        await daily_command(update, MagicMock(user_data={}))

    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_daily_cooldown_blocks_early_claim():
    recent = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=1)
    ).isoformat()
    cm = _make_conn_mock(last_claimed=recent)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.daily.db.get_user", return_value=_make_user()), patch(
        "handlers.daily.db.get_conn", return_value=cm
    ):
        await daily_command(update, MagicMock(user_data={}))

    reply = update.message.reply_text.call_args[0][0]
    assert "⏳" in reply and "available" in reply


@pytest.mark.asyncio
async def test_daily_grants_coins_on_first_claim():
    cm = _make_conn_mock(last_claimed=None)
    coins = _daily_coins(1)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch(
        "handlers.daily.db.get_user", side_effect=[_make_user(), _make_user(coins=100 + coins)]
    ), patch("handlers.daily.db.get_conn", return_value=cm):
        await daily_command(update, MagicMock(user_data={}))

    reply = update.message.reply_text.call_args[0][0]
    assert str(coins) in reply
    assert "Day 1" in reply


@pytest.mark.asyncio
async def test_daily_grants_coins_after_cooldown_expires():
    old = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=DAILY_COOLDOWN_HOURS + 1)
    ).isoformat()
    cm = _make_conn_mock(last_claimed=old)
    coins = _daily_coins(1)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch(
        "handlers.daily.db.get_user",
        side_effect=[_make_user(coins=200), _make_user(coins=200 + coins)],
    ), patch("handlers.daily.db.get_conn", return_value=cm):
        await daily_command(update, MagicMock(user_data={}))

    reply = update.message.reply_text.call_args[0][0]
    assert str(coins) in reply


@pytest.mark.asyncio
async def test_daily_streak_increments_on_consecutive_claim():
    """Claiming within 48h should increment streak."""
    last = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=25)
    ).isoformat()
    cm = _make_conn_mock(last_claimed=last)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch(
        "handlers.daily.db.get_user",
        side_effect=[_make_user(daily_streak=2), _make_user(coins=150, daily_streak=3)],
    ), patch("handlers.daily.db.get_conn", return_value=cm):
        await daily_command(update, MagicMock(user_data={}))

    reply = update.message.reply_text.call_args[0][0]
    assert "Day 3" in reply


@pytest.mark.asyncio
async def test_daily_streak_resets_after_missed_day():
    """Claiming after 48h should reset streak to 1."""
    old = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=49)
    ).isoformat()
    cm = _make_conn_mock(last_claimed=old)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch(
        "handlers.daily.db.get_user",
        side_effect=[_make_user(daily_streak=5), _make_user(coins=150, daily_streak=1)],
    ), patch("handlers.daily.db.get_conn", return_value=cm):
        await daily_command(update, MagicMock(user_data={}))

    reply = update.message.reply_text.call_args[0][0]
    assert "Day 1" in reply


def test_daily_coins_correct_per_tier():
    assert _daily_coins(1) == 50
    assert _daily_coins(2) == 50
    assert _daily_coins(3) == 75
    assert _daily_coins(6) == 75
    assert _daily_coins(7) == 100
    assert _daily_coins(13) == 100
    assert _daily_coins(14) == 150
    assert _daily_coins(30) == 150


def test_daily_cooldown_constant():
    assert DAILY_COOLDOWN_HOURS == 24
    assert DAILY_TIERS[0] == (14, 150)
