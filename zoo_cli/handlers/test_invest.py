import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.invest import invest_command, invest_deposit_callback, invest_collect_callback


def _make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_ctx(args=None):
    ctx = MagicMock()
    ctx.args = args or []
    ctx.user_data = {}
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
    with patch("handlers.invest.db.get_user", return_value=_make_user()), patch(
        "handlers.invest.db.get_active_investment", return_value=None
    ):
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


# ── invest_deposit_callback / invest_collect_callback ─────────────────────────


def _make_callback(user_id=1, data="invest_deposit_100"):
    query = MagicMock()
    query.from_user.id = user_id
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    return update, query, ctx


@pytest.mark.asyncio
async def test_invest_deposit_callback_creates_investment():
    update, query, ctx = _make_callback(data="invest_deposit_100")
    inv = {"id": 1, "amount": 100, "return_amount": 125, "invested_at": "2099-01-01T00:00:00"}
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.invest.db.get_active_investment", side_effect=[None, inv]
    ), patch("handlers.invest.db.create_investment") as mock_create, patch(
        "handlers.invest.db.add_coins"
    ):
        await invest_deposit_callback(update, ctx)
    mock_create.assert_called_once()
    query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_invest_deposit_callback_blocked_when_active():
    update, query, ctx = _make_callback(data="invest_deposit_100")
    existing = {"id": 1, "amount": 50, "return_amount": 63, "invested_at": "2099-01-01T00:00:00"}
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.invest.db.get_active_investment", return_value=existing
    ):
        await invest_deposit_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_invest_collect_callback_succeeds():
    update, query, ctx = _make_callback(data="invest_collect")
    past = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=25)
    ).isoformat()
    inv = {"id": 1, "amount": 100, "return_amount": 125, "invested_at": past}
    with patch("handlers.invest.db.get_user", return_value=_make_user()), patch(
        "handlers.invest.db.get_active_investment", return_value=inv
    ), patch("handlers.invest.db.collect_investment") as mock_collect, patch(
        "handlers.invest.db.add_coins"
    ):
        await invest_collect_callback(update, ctx)
    mock_collect.assert_called_once_with(1)
    query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_invest_collect_callback_blocked_when_not_ready():
    update, query, ctx = _make_callback(data="invest_collect")
    future = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    inv = {"id": 1, "amount": 100, "return_amount": 125, "invested_at": future}
    with patch("handlers.invest.db.get_user", return_value=_make_user()), patch(
        "handlers.invest.db.get_active_investment", return_value=inv
    ):
        await invest_collect_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_invest_unregistered_user():
    update = _make_update()
    ctx = _make_ctx(args=[])
    with patch("handlers.invest.db.get_user", return_value=None):
        await invest_command(update, ctx)
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_invest_below_minimum():
    update = _make_update()
    ctx = _make_ctx(args=["5"])
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.invest.db.get_active_investment", return_value=None
    ):
        await invest_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "minimum" in reply.lower()


@pytest.mark.asyncio
async def test_invest_collect_no_investment():
    update, query, ctx = _make_callback(data="invest_collect")
    with patch("handlers.invest.db.get_user", return_value=_make_user()), patch(
        "handlers.invest.db.get_active_investment", return_value=None
    ):
        await invest_collect_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


# ── invest_max_callback ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invest_max_callback_creates_investment():
    from handlers.invest import invest_max_callback

    update, query, ctx = _make_callback(data="invest_max")
    inv = {"id": 1, "amount": 500, "return_amount": 625, "invested_at": "2099-01-01T00:00:00"}
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.invest.db.get_active_investment", side_effect=[None, inv]
    ), patch("handlers.invest.db.create_investment") as mock_create, patch(
        "handlers.invest.db.add_coins"
    ):
        await invest_max_callback(update, ctx)
    mock_create.assert_called_once()
    query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_invest_max_callback_no_user():
    from handlers.invest import invest_max_callback

    update, query, ctx = _make_callback(data="invest_max")
    with patch("handlers.invest.db.get_user", return_value=None):
        await invest_max_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_invest_max_callback_already_active():
    from handlers.invest import invest_max_callback

    update, query, ctx = _make_callback(data="invest_max")
    existing = {"id": 1, "amount": 100, "return_amount": 125, "invested_at": "2099-01-01T00:00:00"}
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.invest.db.get_active_investment", return_value=existing
    ):
        await invest_max_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_invest_max_callback_below_minimum():
    from handlers.invest import invest_max_callback

    update, query, ctx = _make_callback(data="invest_max")
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=5)), patch(
        "handlers.invest.db.get_active_investment", return_value=None
    ):
        await invest_max_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True


@pytest.mark.asyncio
async def test_invest_deposit_callback_insufficient_coins():
    update, query, ctx = _make_callback(data="invest_deposit_1000")
    with patch("handlers.invest.db.get_user", return_value=_make_user(coins=50)), patch(
        "handlers.invest.db.get_active_investment", return_value=None
    ):
        await invest_deposit_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_invest_deposit_callback_no_user():
    from handlers.invest import invest_deposit_callback

    update, query, ctx = _make_callback(data="invest_deposit_100")
    with patch("handlers.invest.db.get_user", return_value=None):
        await invest_deposit_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
