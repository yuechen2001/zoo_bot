import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.slots import (
    slots_command,
    slots_spin_callback,
    _spin_result,
    SPIN_COST,
    WIN_3,
    WIN_2,
    SYMBOLS,
)


# ── constants ──────────────────────────────────────────────────────────────────


def test_spin_cost_is_10():
    assert SPIN_COST == 10


def test_win_3_is_150():
    assert WIN_3 == 150


def test_win_2_is_10():
    assert WIN_2 == 10


def test_symbols_has_6_entries():
    assert len(SYMBOLS) == 6


def test_symbols_are_unique():
    assert len(set(SYMBOLS)) == len(SYMBOLS)


# ── _spin_result unit tests ────────────────────────────────────────────────────


def test_spin_result_three_of_a_kind():
    winnings, msg = _spin_result(["🐼", "🐼", "🐼"])
    assert winnings == WIN_3
    assert "JACKPOT" in msg


def test_spin_result_two_of_a_kind():
    winnings, msg = _spin_result(["🐼", "🐼", "🐭"])
    assert winnings == WIN_2
    assert "Two of a kind" in msg


def test_spin_result_no_match():
    winnings, msg = _spin_result(["🐭", "🐸", "🐱"])
    assert winnings == 0
    assert "No match" in msg or "luck" in msg.lower()


# ── slots_command ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_slots_rejects_unknown_user():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.slots.db.get_user", return_value=None):
        await slots_command(update, MagicMock())

    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_slots_rejects_insufficient_coins():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.slots.db.get_user", return_value={"coins": SPIN_COST - 1}):
        await slots_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert str(SPIN_COST) in reply


@pytest.mark.asyncio
async def test_slots_command_shows_spin_button():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.slots.db.get_user", return_value={"coins": 100}):
        await slots_command(update, MagicMock(user_data={}))

    kwargs = update.message.reply_text.call_args[1]
    kb = kwargs["reply_markup"]
    button_data = kb.inline_keyboard[0][0].callback_data
    assert button_data == "slots_spin"


# ── slots_spin_callback payout paths ──────────────────────────────────────────


def _make_spin_query(coins: int = 100):
    query = MagicMock()
    query.from_user.id = 1
    query.data = "slots_spin"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    user = {"coins": coins}
    return update, query, user


@pytest.mark.asyncio
async def test_slots_spin_callback_three_of_a_kind():
    update, query, user = _make_spin_query(100)
    after = {"coins": 100 - SPIN_COST + WIN_3}

    with patch("handlers.slots.db.get_user", side_effect=[user, after]), patch(
        "handlers.slots.db.add_coins"
    ), patch("handlers.slots.random.choice", return_value="🐼"):
        await slots_spin_callback(update, MagicMock())

    text = query.edit_message_text.call_args[0][0]
    assert "JACKPOT" in text
    assert str(WIN_3) in text


@pytest.mark.asyncio
async def test_slots_spin_callback_two_of_a_kind():
    update, query, user = _make_spin_query(100)
    after = {"coins": 100 - SPIN_COST + WIN_2}

    with patch("handlers.slots.db.get_user", side_effect=[user, after]), patch(
        "handlers.slots.db.add_coins"
    ), patch("handlers.slots.random.choice", side_effect=["🐼", "🐼", "🐭"]):
        await slots_spin_callback(update, MagicMock())

    text = query.edit_message_text.call_args[0][0]
    assert "Two of a kind" in text
    assert str(WIN_2) in text


@pytest.mark.asyncio
async def test_slots_spin_callback_no_match():
    update, query, user = _make_spin_query(100)
    after = {"coins": 100 - SPIN_COST}

    with patch("handlers.slots.db.get_user", side_effect=[user, after]), patch(
        "handlers.slots.db.add_coins"
    ), patch("handlers.slots.random.choice", side_effect=["🐭", "🐸", "🐱"]):
        await slots_spin_callback(update, MagicMock())

    text = query.edit_message_text.call_args[0][0]
    assert "🐭" in text and "🐸" in text and "🐱" in text


@pytest.mark.asyncio
async def test_slots_spin_callback_insufficient_coins():
    update, query, user = _make_spin_query(SPIN_COST - 1)

    with patch("handlers.slots.db.get_user", return_value=user):
        await slots_spin_callback(update, MagicMock())

    query.edit_message_text.assert_not_called()
    query.answer.assert_called_once()
    assert str(SPIN_COST) in query.answer.call_args[0][0]
