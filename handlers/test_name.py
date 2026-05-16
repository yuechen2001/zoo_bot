import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.name import name_command


def _make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_ctx(args=None):
    ctx = MagicMock()
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
async def test_name_no_args_shows_usage():
    update = _make_update()
    await name_command(update, _make_ctx([]))
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply or "/name" in reply


@pytest.mark.asyncio
async def test_name_non_numeric_position_shows_usage():
    update = _make_update()
    await name_command(update, _make_ctx(["abc", "Fluffy"]))
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply or "/name" in reply


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
