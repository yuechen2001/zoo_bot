import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.sell import sell_command


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
async def test_sell_shows_usage_with_no_args():
    update = _make_update()
    ctx = _make_ctx(args=[])
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "usage" in reply.lower() or "/sell" in reply.lower()


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
        "handlers.sell.db.delete_animal"
    ) as mock_delete, patch(
        "handlers.sell.db.get_conn", return_value=_make_conn_mock()
    ), patch(
        "handlers.sell.check_achievements"
    ):
        await sell_command(update, ctx)
    mock_delete.assert_called_once_with("a1")
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
        "handlers.sell.db.delete_animal"
    ), patch(
        "handlers.sell.db.get_conn", return_value=_make_conn_mock()
    ), patch(
        "handlers.sell.check_achievements"
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
        "handlers.sell.db.delete_animal"
    ), patch(
        "handlers.sell.db.get_conn", return_value=_make_conn_mock()
    ), patch(
        "handlers.sell.check_achievements"
    ):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    # base = 200 // 2 = 100; hunger 100 → price = 100
    assert "100" in reply
