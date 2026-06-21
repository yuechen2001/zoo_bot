import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.start import start_command


def _make_update(chat_type="group", user_id=1, username="alice"):
    update = MagicMock()
    update.effective_chat.type = chat_type
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_user.first_name = username
    update.effective_chat.id = -100
    update.message.reply_text = AsyncMock()
    return update


def _make_conn_mock(species_id=1, emoji="🐭", name="Mouse"):
    species_row = MagicMock()
    species_row.__getitem__ = MagicMock(
        side_effect=lambda k: {"species_id": species_id, "emoji": emoji, "name": name}[k]
    )
    inner = MagicMock()
    inner.execute.return_value.fetchall.return_value = [species_row]
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_start_in_private_chat_redirects():
    update = _make_update(chat_type="private")
    await start_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "group" in reply.lower()


@pytest.mark.asyncio
async def test_start_returning_user_shows_welcome_back():
    update = _make_update()
    existing_animal = MagicMock()
    with patch("handlers.start.db.ensure_user"), patch(
        "handlers.start.db.get_animals", return_value=[existing_animal]
    ):
        await start_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "Welcome back" in reply or "zoo" in reply.lower()


@pytest.mark.asyncio
async def test_start_new_user_gets_starter_animal():
    update = _make_update()
    with patch("handlers.start.db.ensure_user"), patch(
        "handlers.start.db.get_animals", return_value=[]
    ), patch("handlers.start.db.get_conn", return_value=_make_conn_mock()), patch(
        "handlers.start.db.give_starter_enclosures"
    ):
        await start_command(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "Welcome" in reply or "Zoo Bot" in reply
    assert "100" in reply  # starter coins


@pytest.mark.asyncio
async def test_start_new_user_calls_give_starter_enclosures():
    update = _make_update()
    with patch("handlers.start.db.ensure_user"), patch(
        "handlers.start.db.get_animals", return_value=[]
    ), patch("handlers.start.db.get_conn", return_value=_make_conn_mock()), patch(
        "handlers.start.db.give_starter_enclosures"
    ) as mock_enc:
        await start_command(update, MagicMock())
    mock_enc.assert_called_once_with(1)
