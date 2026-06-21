import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.autofeed import autofeed_command


def _make_update(args):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock(user_data={})
    ctx.args = args
    return update, ctx


@pytest.mark.asyncio
async def test_autofeed_no_user():
    update, ctx = _make_update(["50", "100"])
    with patch("handlers.autofeed.db.get_user", return_value=None):
        await autofeed_command(update, ctx)
    update.message.reply_text.assert_called_once()
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_autofeed_sets_threshold_and_max_coins():
    update, ctx = _make_update(["50", "100"])
    with patch("handlers.autofeed.db.get_user", return_value={"coins": 200}), patch(
        "handlers.autofeed.db.set_autofeed"
    ) as mock_set:
        await autofeed_command(update, ctx)
    mock_set.assert_called_once_with(1, 50, 100)
    reply = update.message.reply_text.call_args[0][0]
    assert "50" in reply
    assert "100" in reply


@pytest.mark.asyncio
async def test_autofeed_off_disables():
    update, ctx = _make_update(["off"])
    with patch("handlers.autofeed.db.get_user", return_value={"coins": 200}), patch(
        "handlers.autofeed.db.set_autofeed"
    ) as mock_set:
        await autofeed_command(update, ctx)
    mock_set.assert_called_once_with(1, None, None)
    reply = update.message.reply_text.call_args[0][0]
    assert "disabled" in reply.lower()


@pytest.mark.asyncio
async def test_autofeed_off_case_insensitive():
    update, ctx = _make_update(["OFF"])
    with patch("handlers.autofeed.db.get_user", return_value={"coins": 200}), patch(
        "handlers.autofeed.db.set_autofeed"
    ) as mock_set:
        await autofeed_command(update, ctx)
    mock_set.assert_called_once_with(1, None, None)


@pytest.mark.asyncio
async def test_autofeed_no_args_shows_usage():
    update, ctx = _make_update([])
    with patch("handlers.autofeed.db.get_user", return_value={"coins": 200}):
        await autofeed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply


@pytest.mark.asyncio
async def test_autofeed_one_arg_shows_usage():
    update, ctx = _make_update(["50"])
    with patch("handlers.autofeed.db.get_user", return_value={"coins": 200}):
        await autofeed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply


@pytest.mark.asyncio
async def test_autofeed_threshold_zero_rejected():
    update, ctx = _make_update(["0", "100"])
    with patch("handlers.autofeed.db.get_user", return_value={"coins": 200}):
        await autofeed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "1" in reply and "100" in reply  # boundary message


@pytest.mark.asyncio
async def test_autofeed_threshold_over_100_rejected():
    update, ctx = _make_update(["101", "100"])
    with patch("handlers.autofeed.db.get_user", return_value={"coins": 200}):
        await autofeed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "100" in reply


@pytest.mark.asyncio
async def test_autofeed_max_coins_zero_rejected():
    update, ctx = _make_update(["50", "0"])
    with patch("handlers.autofeed.db.get_user", return_value={"coins": 200}):
        await autofeed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "0" not in reply or "greater" in reply
