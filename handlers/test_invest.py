import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.invest import invest_command


def _make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_ctx(args=None):
    ctx = MagicMock()
    ctx.args = args or []
    return ctx


def _make_user(coins=500):
    return {"user_id": 1, "coins": coins}


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_invest_shows_help_with_no_args():
    update = _make_update()
    ctx = _make_ctx(args=[])
    with patch("handlers.invest.db.get_user", return_value=_make_user()):
        await invest_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "invest" in reply.lower()


@pytest.mark.asyncio
async def test_invest_deducts_coins_and_creates_record():
    update = _make_update()
    ctx = _make_ctx(args=["100"])
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.invest.db.get_active_investment", return_value=None
    ), patch("handlers.invest.db.create_investment") as mock_create, patch(
        "handlers.invest.db.get_conn", return_value=_make_conn_mock()
    ):
        await invest_command(update, ctx)
    mock_create.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "100" in reply
    assert "25%" in reply or "125" in reply


@pytest.mark.asyncio
async def test_invest_blocked_when_active_investment_exists():
    update = _make_update()
    ctx = _make_ctx(args=["100"])
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.invest.db.get_active_investment", return_value={"id": 1, "amount": 50}
    ):
        await invest_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "active" in reply.lower()


@pytest.mark.asyncio
async def test_invest_blocked_when_insufficient_coins():
    update = _make_update()
    ctx = _make_ctx(args=["1000"])
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=50)), patch(
        "handlers.invest.db.get_active_investment", return_value=None
    ):
        await invest_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "enough" in reply.lower() or "coins" in reply.lower()


@pytest.mark.asyncio
async def test_invest_collect_too_early():
    update = _make_update()
    ctx = _make_ctx(args=["collect"])
    inv = {
        "id": 1,
        "amount": 100,
        "return_amount": 125,
        "invested_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(tzinfo=None)
        .isoformat(),
    }
    with patch("handlers.invest.db.get_user", return_value=_make_user()), patch(
        "handlers.invest.db.get_active_investment", return_value=inv
    ):
        await invest_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "not ready" in reply.lower() or "come back" in reply.lower()


@pytest.mark.asyncio
async def test_invest_collect_success():
    update = _make_update()
    ctx = _make_ctx(args=["collect"])
    past = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=25)
    ).isoformat()
    inv = {"id": 1, "amount": 100, "return_amount": 125, "invested_at": past}
    with patch("handlers.invest.db.get_user", return_value=_make_user()), patch(
        "handlers.invest.db.get_active_investment", return_value=inv
    ), patch("handlers.invest.db.collect_investment") as mock_collect, patch(
        "handlers.invest.db.get_conn", return_value=_make_conn_mock()
    ):
        await invest_command(update, ctx)
    mock_collect.assert_called_once_with(1)
    reply = update.message.reply_text.call_args[0][0]
    assert "125" in reply
    assert "25" in reply  # profit


@pytest.mark.asyncio
async def test_invest_unknown_arg_shows_status_card():
    """Unknown args now show the interactive status card."""
    update = _make_update()
    ctx = _make_ctx(args=["status"])
    with patch("handlers.invest.db.get_user", return_value=_make_user()), patch(
        "handlers.invest.db.get_active_investment", return_value=None
    ):
        await invest_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "invest" in reply.lower()
