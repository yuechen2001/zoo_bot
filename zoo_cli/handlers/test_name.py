import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.name import name_command, name_pick_callback, name_cancel_callback, name_text_handler


def _make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_ctx(args=None):
    ctx = MagicMock(user_data={})
    ctx.args = args or []
    return ctx


def _make_animal(emoji="🐭", animal_id="a1"):
    return {"animal_id": animal_id, "emoji": emoji}


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_name_no_args_shows_picker_or_empty():
    update = _make_update()
    with patch("handlers.name.db.get_animals", return_value=[]):
        await name_command(update, _make_ctx([]))
    reply = update.message.reply_text.call_args[0][0]
    assert "no animal" in reply.lower()


@pytest.mark.asyncio
async def test_name_non_numeric_position_shows_picker():
    update = _make_update()
    with patch("handlers.name.db.get_animals", return_value=[]):
        await name_command(update, _make_ctx(["abc", "Fluffy"]))
    reply = update.message.reply_text.call_args[0][0]
    assert "no animal" in reply.lower()


@pytest.mark.asyncio
async def test_name_invalid_position():
    update = _make_update()
    with patch("handlers.name.db.get_animal_by_position", return_value=None), patch(
        "handlers.name.db.get_animals", return_value=[]
    ):
        await name_command(update, _make_ctx(["99", "Fluffy"]))
    reply = update.message.reply_text.call_args[0][0]
    assert "No animal" in reply or "#99" in reply


@pytest.mark.asyncio
async def test_name_renames_animal():
    update = _make_update()
    animal = _make_animal(emoji="🐭")
    with patch("handlers.name.db.get_animal_by_position", return_value=animal), patch(
        "handlers.name.db.get_conn", return_value=_make_conn_mock()
    ):
        await name_command(update, _make_ctx(["1", "Fluffy"]))
    reply = update.message.reply_text.call_args[0][0]
    assert "Fluffy" in reply


@pytest.mark.asyncio
async def test_name_truncates_to_20_chars():
    update = _make_update()
    animal = _make_animal()
    long_name = "A" * 30
    with patch("handlers.name.db.get_animal_by_position", return_value=animal), patch(
        "handlers.name.db.get_conn", return_value=_make_conn_mock()
    ):
        await name_command(update, _make_ctx(["1", long_name]))
    reply = update.message.reply_text.call_args[0][0]
    assert "A" * 20 in reply
    assert "A" * 21 not in reply


# ── name_pick_callback / name_text_handler ────────────────────────────────────


def _make_callback(user_id=1, data="name_pick_1"):
    query = MagicMock()
    query.from_user.id = user_id
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.user_data = {}
    return update, query, ctx


@pytest.mark.asyncio
async def test_name_pick_stores_pending_and_edits():
    update, query, ctx = _make_callback(data="name_pick_2")
    animal = _make_animal(emoji="🐭")
    animal["nickname"] = None
    animal["species_name"] = "Mouse"
    with patch("handlers.name.db.get_animal_by_position", return_value=animal):
        await name_pick_callback(update, ctx)
    assert ctx.user_data["pending_name"]["pos"] == 2
    query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_name_pick_missing_animal_shows_alert():
    update, query, ctx = _make_callback(data="name_pick_5")
    with patch("handlers.name.db.get_animal_by_position", return_value=None):
        await name_pick_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_name_cancel_clears_pending():
    update, query, ctx = _make_callback(data="name_cancel")
    ctx.user_data["pending_name"] = {"pos": 1}
    await name_cancel_callback(update, ctx)
    assert "pending_name" not in ctx.user_data
    query.edit_message_text.assert_called_once_with("Naming cancelled.")


@pytest.mark.asyncio
async def test_name_text_handler_saves_nickname():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.text = "Buddy"
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.user_data = {"pending_name": {"pos": 1}}
    animal = _make_animal(emoji="🐭")
    with patch("handlers.name.db.get_animal_by_position", return_value=animal), patch(
        "handlers.name.db.get_conn", return_value=_make_conn_mock()
    ):
        await name_text_handler(update, ctx)
    assert "pending_name" not in ctx.user_data
    reply = update.message.reply_text.call_args[0][0]
    assert "Buddy" in reply


@pytest.mark.asyncio
async def test_name_text_handler_ignores_without_pending():
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.user_data = {}
    await name_text_handler(update, ctx)
    update.message.reply_text.assert_not_called()
