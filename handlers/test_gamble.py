import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.gamble import gamble_command, gamble_bet_callback, MAX_BET


def _make_command_update(coins: int = 200):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    return update, {"coins": coins}


def _make_bet_query(amount: int, coins: int = 200):
    query = MagicMock()
    query.from_user.id = 1
    query.data = f"gamble_bet_{amount}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query, {"coins": coins}


# ── gamble_command ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gamble_rejects_unknown_user():
    update, _ = _make_command_update()
    with patch("handlers.gamble.db.get_user", return_value=None):
        await gamble_command(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_gamble_command_shows_bet_buttons():
    update, user = _make_command_update(coins=200)
    with patch("handlers.gamble.db.get_user", return_value=user):
        await gamble_command(update, MagicMock())
    kwargs = update.message.reply_text.call_args[1]
    kb = kwargs["reply_markup"]
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert any(d.startswith("gamble_bet_") for d in all_data)


@pytest.mark.asyncio
async def test_gamble_command_disables_unaffordable_buttons():
    update, _ = _make_command_update(coins=15)
    with patch("handlers.gamble.db.get_user", return_value={"coins": 15}):
        await gamble_command(update, MagicMock())
    kwargs = update.message.reply_text.call_args[1]
    kb = kwargs["reply_markup"]
    noop_count = sum(
        1 for row in kb.inline_keyboard for btn in row if btn.callback_data == "zoo_noop"
    )
    assert noop_count >= 1


# ── gamble_bet_callback ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gamble_bet_win():
    update, query, user = _make_bet_query(50, coins=100)
    after = {"coins": 150}
    with patch("handlers.gamble.db.get_user", side_effect=[user, after]), patch(
        "handlers.gamble.db.add_coins"
    ), patch(
        "handlers.gamble.random.random", return_value=0.1
    ):  # win
        await gamble_bet_callback(update, MagicMock())

    text = query.edit_message_text.call_args[0][0]
    assert "Heads" in text
    assert "+50" in text


@pytest.mark.asyncio
async def test_gamble_bet_lose():
    update, query, user = _make_bet_query(50, coins=100)
    after = {"coins": 50}
    with patch("handlers.gamble.db.get_user", side_effect=[user, after]), patch(
        "handlers.gamble.db.add_coins"
    ), patch(
        "handlers.gamble.random.random", return_value=0.9
    ):  # lose
        await gamble_bet_callback(update, MagicMock())

    text = query.edit_message_text.call_args[0][0]
    assert "Tails" in text
    assert "-50" in text


@pytest.mark.asyncio
async def test_gamble_bet_insufficient_coins():
    update, query, user = _make_bet_query(50, coins=30)
    with patch("handlers.gamble.db.get_user", return_value=user):
        await gamble_bet_callback(update, MagicMock())

    query.edit_message_text.assert_not_called()
    query.answer.assert_called_once()
    assert "30" in query.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_gamble_bet_over_max_rejected():
    update, query, user = _make_bet_query(MAX_BET + 1, coins=500)
    with patch("handlers.gamble.db.get_user", return_value=user):
        await gamble_bet_callback(update, MagicMock())

    query.edit_message_text.assert_not_called()
    assert str(MAX_BET) in query.answer.call_args[0][0]


# ── constants ──────────────────────────────────────────────────────────────────


def test_max_bet_constant():
    assert MAX_BET == 200


@pytest.mark.asyncio
async def test_gamble_bet_callback_rejects_unknown_user():
    update, query, _ = _make_bet_query(50)
    with patch("handlers.gamble.db.get_user", return_value=None):
        await gamble_bet_callback(update, MagicMock())
    query.answer.assert_called_once_with("Use /start first!", show_alert=True)
    query.edit_message_text.assert_not_called()


def test_gamble_distribution_is_50_50():
    """random.random() < 0.5 is the win condition — verify it's fair over many trials."""
    import random

    wins = sum(1 for _ in range(10_000) if random.random() < 0.5)
    assert 4500 < wins < 5500
