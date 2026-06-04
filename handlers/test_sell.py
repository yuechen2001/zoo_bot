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


def _make_animal(
    catch_cost=20,
    hunger=100,
    is_breeding=0,
    nickname="Mouse",
    emoji="🐭",
    animal_id="a1",
    user_id=1,
):
    return {
        "animal_id": animal_id,
        "user_id": user_id,
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
async def test_sell_no_animals_shows_empty_message():
    update = _make_update()
    ctx = _make_ctx(args=[])
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animals", return_value=[]
    ):
        await sell_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "no animal" in reply.lower()


@pytest.mark.asyncio
async def test_sell_shows_picker_when_animals_exist():
    update = _make_update()
    ctx = _make_ctx(args=[])
    animal = _make_animal()
    with patch("handlers.sell.db.get_user", return_value={"coins": 100}), patch(
        "handlers.sell.db.get_animals", return_value=[animal]
    ):
        await sell_command(update, ctx)
    # Should show picker, not an error
    reply = update.message.reply_text.call_args[0][0]
    assert "sell" in reply.lower()


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
    update, query, ctx = _make_callback(data="sell_yes_a1")
    animal = _make_animal(catch_cost=20, hunger=100)
    with patch("handlers.sell.db.get_animal", return_value=animal), patch(
        "handlers.sell.db.has_pending_trade_for_animal", return_value=False
    ), patch("handlers.sell.db.sell_animal") as mock_sell, patch(
        "handlers.sell.db.get_animals", return_value=[]
    ):
        await sell_yes_callback(update, ctx)
    mock_sell.assert_called_once_with(1, "a1", 10)
    query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_sell_yes_rejects_wrong_owner():
    """sell_yes_ callback must reject if animal belongs to a different user."""
    update, query, ctx = _make_callback(user_id=2, data="sell_yes_a1")
    animal = _make_animal(catch_cost=20, hunger=100, user_id=1)  # owned by user 1
    with patch("handlers.sell.db.get_animal", return_value=animal), patch(
        "handlers.sell.db.sell_animal"
    ) as mock_sell:
        await sell_yes_callback(update, ctx)
    mock_sell.assert_not_called()
    query.answer.assert_called_once()
    assert query.answer.call_args[1].get("show_alert") is True


@pytest.mark.asyncio
async def test_sell_cancel_dismisses():
    update, query, ctx = _make_callback(data="sell_cancel")
    await sell_cancel_callback(update, ctx)
    query.answer.assert_called_once_with("Cancelled")
    query.edit_message_text.assert_called_once_with("Sell cancelled.")


@pytest.mark.asyncio
async def test_sell_command_unregistered_user():
    update = _make_update()
    ctx = _make_ctx()
    with patch("handlers.sell.db.get_user", return_value=None):
        await sell_command(update, ctx)
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_sell_pick_animal_not_found():
    update, query, ctx = _make_callback(data="sell_pick_99")
    with patch("handlers.sell.db.get_animal_by_position", return_value=None):
        await sell_pick_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_sell_pick_has_pending_trade():
    update, query, ctx = _make_callback(data="sell_pick_1")
    animal = _make_animal()
    with patch("handlers.sell.db.get_animal_by_position", return_value=animal), patch(
        "handlers.sell.db.has_pending_trade_for_animal", return_value=True
    ):
        await sell_pick_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_sell_yes_animal_not_found():
    update, query, ctx = _make_callback(data="sell_yes_a1")
    with patch("handlers.sell.db.get_animal", return_value=None), patch(
        "handlers.sell.db.sell_animal"
    ) as mock_sell:
        await sell_yes_callback(update, ctx)
    mock_sell.assert_not_called()
    assert query.answer.call_args[1].get("show_alert") is True


@pytest.mark.asyncio
async def test_sell_yes_is_breeding():
    update, query, ctx = _make_callback(data="sell_yes_a1")
    animal = _make_animal(is_breeding=1)
    with patch("handlers.sell.db.get_animal", return_value=animal), patch(
        "handlers.sell.db.sell_animal"
    ) as mock_sell:
        await sell_yes_callback(update, ctx)
    mock_sell.assert_not_called()
    assert query.answer.call_args[1].get("show_alert") is True


@pytest.mark.asyncio
async def test_sell_yes_has_pending_trade():
    update, query, ctx = _make_callback(data="sell_yes_a1")
    animal = _make_animal()
    with patch("handlers.sell.db.get_animal", return_value=animal), patch(
        "handlers.sell.db.has_pending_trade_for_animal", return_value=True
    ), patch("handlers.sell.db.sell_animal") as mock_sell:
        await sell_yes_callback(update, ctx)
    mock_sell.assert_not_called()
    assert query.answer.call_args[1].get("show_alert") is True


@pytest.mark.asyncio
async def test_sell_page_callback():
    from handlers.sell import sell_page_callback

    query = MagicMock()
    query.from_user.id = 1
    query.data = "sell_page_1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()

    animal = _make_animal()
    with patch("handlers.sell.db.get_animals", return_value=[animal]):
        await sell_page_callback(update, ctx)
    query.edit_message_text.assert_called_once()
    assert "sell" in query.edit_message_text.call_args[0][0].lower()
