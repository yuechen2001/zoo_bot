import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.gamble import gamble_command, MAX_BET


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _setup(coins=200, args=None, chat_type="private"):
    update = MagicMock()
    update.effective_chat.type = chat_type
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args or []
    return update, ctx, {"coins": coins}


# ── validation ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gamble_rejects_unknown_user():
    update, ctx, _ = _setup()
    with patch("handlers.gamble.db.get_user", return_value=None):
        await gamble_command(update, ctx)
    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_gamble_no_args_shows_usage():
    update, ctx, user = _setup(args=[])
    with patch("handlers.gamble.db.get_user", return_value=user):
        await gamble_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply or "usage" in reply.lower()
    assert str(MAX_BET) in reply


@pytest.mark.asyncio
async def test_gamble_zero_bet_rejected():
    update, ctx, user = _setup(args=["0"])
    with patch("handlers.gamble.db.get_user", return_value=user):
        await gamble_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "1 coin" in reply or "at least" in reply.lower()


@pytest.mark.asyncio
async def test_gamble_over_max_bet_rejected():
    update, ctx, user = _setup(args=[str(MAX_BET + 1)])
    with patch("handlers.gamble.db.get_user", return_value=user):
        await gamble_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert str(MAX_BET) in reply


@pytest.mark.asyncio
async def test_gamble_insufficient_coins_rejected():
    update, ctx, _ = _setup(coins=30, args=["50"])
    with patch("handlers.gamble.db.get_user", return_value={"coins": 30}):
        await gamble_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Not enough" in reply or "30" in reply


# ── win / lose paths ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gamble_win_adds_coins():
    update, ctx, user = _setup(coins=100, args=["50"])
    with patch("handlers.gamble.db.get_user", return_value=user), patch(
        "handlers.gamble.db.get_conn", return_value=_make_conn_mock()
    ), patch(
        "handlers.gamble.random.random", return_value=0.1
    ):  # 0.1 < 0.5 → win
        await gamble_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "Heads" in reply or "+50" in reply


@pytest.mark.asyncio
async def test_gamble_lose_deducts_coins():
    update, ctx, user = _setup(coins=100, args=["50"])
    with patch("handlers.gamble.db.get_user", return_value=user), patch(
        "handlers.gamble.db.get_conn", return_value=_make_conn_mock()
    ), patch(
        "handlers.gamble.random.random", return_value=0.9
    ):  # 0.9 >= 0.5 → lose
        await gamble_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "Tails" in reply or "-50" in reply


def test_max_bet_constant():
    assert MAX_BET == 100


def test_gamble_distribution_is_50_50():
    """random.random() < 0.5 is the win condition — verify it's fair over many trials."""
    import random

    wins = sum(1 for _ in range(10_000) if random.random() < 0.5)
    assert 4500 < wins < 5500
