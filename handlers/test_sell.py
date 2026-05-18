import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.sell import sell_command, sell_pick_callback, sell_yes_callback, sell_cancel_callback


@pytest.fixture(autouse=True)
def no_achievements(monkeypatch):
    monkeypatch.setattr("handlers.sell.check_achievements", AsyncMock())


def _make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_ctx(args=None):
    ctx = MagicMock()
    ctx.args = args or []
    return ctx


def _make_animal(catch_cost=20, hunger=100, is_breeding=0, nickname="Mouse", emoji="🐭"):
    return {
        "animal_id": "a1",
        "species_name": "Mouse",
        "nickname": nickname,
        "emoji": emoji,
        "rarity": "common",
        "catch_cost": catch_cost,
        "hunger": hunger,
        "is_breeding": is_breeding,
    }


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_sell_no_args_shows_picker_or_empty():
    update = _make_update()
    ctx = _make_ctx(args=[])
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animals", return_value=[]
    ):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "no animal" in reply.lower()


@pytest.mark.asyncio
async def test_sell_invalid_position():
    update = _make_update()
    ctx = _make_ctx(args=["99"])
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animal_by_position", return_value=None
    ):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "no animal" in reply.lower() or "position" in reply.lower()


@pytest.mark.asyncio
async def test_sell_blocked_for_breeding_animal():
    update = _make_update()
    ctx = _make_ctx(args=["1"])
    animal = _make_animal(is_breeding=1)
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animal_by_position", return_value=animal
    ):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "breeding" in reply.lower()


@pytest.mark.asyncio
async def test_sell_blocked_for_animal_in_trade():
    update = _make_update()
    ctx = _make_ctx(args=["1"])
    animal = _make_animal()
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animal_by_position", return_value=animal
    ), patch("handlers.sell.db.has_pending_trade_for_animal", return_value=True):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "trade" in reply.lower()


@pytest.mark.asyncio
async def test_sell_full_hunger_earns_half_catch_cost():
    update = _make_update()
    ctx = _make_ctx(args=["1"])
    animal = _make_animal(catch_cost=20, hunger=100)
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animal_by_position", return_value=animal
    ), patch("handlers.sell.db.has_pending_trade_for_animal", return_value=False), patch(
        "handlers.sell.db.sell_animal"
    ) as mock_sell:
        await sell_command(update, ctx)
    mock_sell.assert_called_once_with(1, "a1", 10)
    # base = catch_cost // 2 = 10; hunger 100 → price = 10
    reply = update.message.reply_text.call_args[0][0]
    assert "10" in reply


@pytest.mark.asyncio
async def test_sell_low_hunger_reduces_price():
    update = _make_update()
    ctx = _make_ctx(args=["1"])
    animal = _make_animal(catch_cost=40, hunger=50)
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animal_by_position", return_value=animal
    ), patch("handlers.sell.db.has_pending_trade_for_animal", return_value=False), patch(
        "handlers.sell.db.sell_animal"
    ):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    # base = 40 // 2 = 20; hunger 50 → price = max(1, round(20 * 50/100)) = 10
    assert "10" in reply


@pytest.mark.asyncio
async def test_sell_legendary_full_hunger():
    update = _make_update()
    ctx = _make_ctx(args=["1"])
    animal = _make_animal(catch_cost=200, hunger=100, nickname="Drgn", emoji="🐉")
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animal_by_position", return_value=animal
    ), patch("handlers.sell.db.has_pending_trade_for_animal", return_value=False), patch(
        "handlers.sell.db.sell_animal"
    ):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    # base = 200 // 2 = 100; hunger 100 → price = 100
    assert "100" in reply


# ── sell_pick_callback ────────────────────────────────────────────────────────


def _make_callback(user_id=1, data="sell_pick_1"):
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
async def test_sell_pick_shows_confirmation():
    update, query, ctx = _make_callback(data="sell_pick_1")
    animal = _make_animal(catch_cost=20, hunger=100)
    with patch("handlers.sell.db.get_animal_by_position", return_value=animal), patch(
        "handlers.sell.db.has_pending_trade_for_animal", return_value=False
    ):
        await sell_pick_callback(update, ctx)
    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args[0][0]
    assert "10" in text  # sell_price = 20//2 * 100/100 = 10


@pytest.mark.asyncio
async def test_sell_pick_blocked_for_breeding():
    update, query, ctx = _make_callback(data="sell_pick_1")
    animal = _make_animal(is_breeding=1)
    with patch("handlers.sell.db.get_animal_by_position", return_value=animal):
        await sell_pick_callback(update, ctx)
    query.answer.assert_called_once()
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_sell_yes_executes_sell():
    update, query, ctx = _make_callback(data="sell_yes_1")
    animal = _make_animal(catch_cost=20, hunger=100)
    with patch("handlers.sell.db.get_animal_by_position", return_value=animal), patch(
        "handlers.sell.db.has_pending_trade_for_animal", return_value=False
    ), patch("handlers.sell.db.sell_animal") as mock_sell:
        await sell_yes_callback(update, ctx)
    mock_sell.assert_called_once_with(1, "a1", 10)
    query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_sell_cancel_dismisses():
    update, query, ctx = _make_callback(data="sell_cancel")
    await sell_cancel_callback(update, ctx)
    query.answer.assert_called_once_with("Cancelled")
    query.edit_message_text.assert_called_once_with("Sell cancelled.")
