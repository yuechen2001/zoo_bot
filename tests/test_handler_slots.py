import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.slots import slots_command, SPIN_COST, WIN_3, WIN_2, SYMBOLS


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


# ── constants ──────────────────────────────────────────────────────────────────


def test_spin_cost_is_10():
    assert SPIN_COST == 10


def test_win_3_is_200():
    assert WIN_3 == 200


def test_win_2_is_20():
    assert WIN_2 == 20


def test_symbols_has_6_entries():
    assert len(SYMBOLS) == 6


def test_symbols_are_unique():
    assert len(set(SYMBOLS)) == len(SYMBOLS)


# ── validation ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_slots_rejects_unknown_user():
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.slots.db.get_user", return_value=None):
        await slots_command(update, MagicMock())

    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_slots_rejects_insufficient_coins():
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.slots.db.get_user", return_value={"coins": SPIN_COST - 1}):
        await slots_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert str(SPIN_COST) in reply


# ── payout paths ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_slots_three_of_a_kind_pays_win3():
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    after_user = {"coins": 100 - SPIN_COST + WIN_3}

    with patch("handlers.slots.db.get_user", side_effect=[{"coins": 100}, after_user]), patch(
        "handlers.slots.db.get_conn", return_value=_make_conn_mock()
    ), patch("handlers.slots.random.choice", return_value="🐼"):
        await slots_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "JACKPOT" in reply
    assert str(WIN_3) in reply


@pytest.mark.asyncio
async def test_slots_two_of_a_kind_pays_win2():
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    after_user = {"coins": 100 - SPIN_COST + WIN_2}

    with patch("handlers.slots.db.get_user", side_effect=[{"coins": 100}, after_user]), patch(
        "handlers.slots.db.get_conn", return_value=_make_conn_mock()
    ), patch("handlers.slots.random.choice", side_effect=["🐼", "🐼", "🐭"]):
        await slots_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "Two of a kind" in reply
    assert str(WIN_2) in reply


@pytest.mark.asyncio
async def test_slots_no_match_loses_spin_cost():
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    after_user = {"coins": 100 - SPIN_COST}

    with patch("handlers.slots.db.get_user", side_effect=[{"coins": 100}, after_user]), patch(
        "handlers.slots.db.get_conn", return_value=_make_conn_mock()
    ), patch("handlers.slots.random.choice", side_effect=["🐭", "🐸", "🐱"]):
        await slots_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "No match" in reply or "luck" in reply.lower()


@pytest.mark.asyncio
async def test_slots_reply_shows_three_reels():
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    after_user = {"coins": 90}

    with patch("handlers.slots.db.get_user", side_effect=[{"coins": 100}, after_user]), patch(
        "handlers.slots.db.get_conn", return_value=_make_conn_mock()
    ), patch("handlers.slots.random.choice", side_effect=["🐭", "🐸", "🐱"]):
        await slots_command(update, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "🐭" in reply
    assert "🐸" in reply
    assert "🐱" in reply
    assert "|" in reply  # reel separator
