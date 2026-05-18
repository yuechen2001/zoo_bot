import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.wild_event import wild_event_callback
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _make_query(user_id=1, username="tester", event_id=1):
    query = MagicMock()
    query.data = f"wild_catch_{event_id}"
    query.from_user.id = user_id
    query.from_user.username = username
    query.from_user.first_name = username
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query


def _make_event(caught_by=None, species_id=1, group_chat_id=-100):
    return make_row(
        id=1,
        group_chat_id=group_chat_id,
        species_id=species_id,
        message_id=42,
        caught_by_user_id=caught_by,
    )


def _make_species(habitat="woodland", catch_rate=0.9):
    return make_row(species_id=1, name="Frog", emoji="🐸", habitat=habitat, catch_rate=catch_rate)


def _make_user():
    return make_row(user_id=1, username="tester", coins=100, group_chat_id=-100)


@pytest.mark.asyncio
async def test_wild_event_nonexistent():
    update, query = _make_query()
    with patch("handlers.wild_event.db.get_wild_event", return_value=None):
        await wild_event_callback(update, MagicMock())
    query.answer.assert_called_once()
    assert "no longer exists" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_wild_event_already_claimed():
    update, query = _make_query()
    event = _make_event(caught_by=99)
    with patch("handlers.wild_event.db.get_wild_event", return_value=event):
        await wild_event_callback(update, MagicMock())
    query.answer.assert_called_once()
    assert "too slow" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_wild_event_no_user():
    update, query = _make_query()
    event = _make_event()
    with patch("handlers.wild_event.db.get_wild_event", return_value=event), patch(
        "handlers.wild_event.db.get_user", return_value=None
    ):
        await wild_event_callback(update, MagicMock())
    query.answer.assert_called_once()
    assert "/start" in query.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_wild_event_enclosure_full():
    update, query = _make_query()
    event = _make_event()
    species = _make_species(habitat="woodland")
    with patch("handlers.wild_event.db.get_wild_event", return_value=event), patch(
        "handlers.wild_event.db.get_user", return_value=_make_user()
    ), patch("handlers.wild_event.db.get_conn") as mock_conn, patch(
        "handlers.wild_event.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.wild_event.db.get_animal_count_by_habitat", return_value=3
    ):
        inner = MagicMock()
        inner.execute.return_value.fetchone.return_value = species
        mock_conn.return_value.__enter__ = MagicMock(return_value=inner)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        await wild_event_callback(update, MagicMock())
    query.answer.assert_called_once()
    assert "full" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_wild_event_no_lure():
    """User without a matching habitat lure is blocked."""
    update, query = _make_query()
    event = _make_event()
    species = _make_species(habitat="woodland")
    with patch("handlers.wild_event.db.get_wild_event", return_value=event), patch(
        "handlers.wild_event.db.get_user", return_value=_make_user()
    ), patch("handlers.wild_event.db.get_conn") as mock_conn, patch(
        "handlers.wild_event.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.wild_event.db.get_animal_count_by_habitat", return_value=0
    ):
        inner = MagicMock()
        # species first, then lure lookup returns None
        inner.execute.return_value.fetchone.side_effect = [species, None]
        mock_conn.return_value.__enter__ = MagicMock(return_value=inner)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        await wild_event_callback(update, MagicMock())
    query.answer.assert_called_once()
    assert "lure" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_wild_event_race_condition_lost():
    """claim_wild_event returns False if another user claimed first."""
    update, query = _make_query()
    event = _make_event()
    species = _make_species()
    lure_row = make_row(id=1)
    with patch("handlers.wild_event.db.get_wild_event", return_value=event), patch(
        "handlers.wild_event.db.get_user", return_value=_make_user()
    ), patch("handlers.wild_event.db.get_conn") as mock_conn, patch(
        "handlers.wild_event.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.wild_event.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.wild_event.db.claim_wild_event", return_value=False
    ), patch(
        "handlers.wild_event.random.random", return_value=0.0
    ):  # force catch rate pass so we reach claim_wild_event
        inner = MagicMock()
        # species first, then lure lookup
        inner.execute.return_value.fetchone.side_effect = [species, lure_row]
        mock_conn.return_value.__enter__ = MagicMock(return_value=inner)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        await wild_event_callback(update, MagicMock())
    query.answer.assert_called_once()
    assert "too slow" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_wild_event_success():
    update, query = _make_query()
    event = _make_event()
    species = _make_species()
    lure_row = make_row(id=1)
    with patch("handlers.wild_event.db.get_wild_event", return_value=event), patch(
        "handlers.wild_event.db.get_user", return_value=_make_user()
    ), patch("handlers.wild_event.db.get_conn") as mock_conn, patch(
        "handlers.wild_event.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.wild_event.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.wild_event.db.claim_wild_event", return_value=True
    ), patch(
        "handlers.wild_event.db.add_animal"
    ), patch(
        "handlers.wild_event.check_achievements"
    ), patch(
        "handlers.wild_event.random.random", return_value=0.0
    ):
        inner = MagicMock()
        # species first, then lure lookup
        inner.execute.return_value.fetchone.side_effect = [species, lure_row]
        mock_conn.return_value.__enter__ = MagicMock(return_value=inner)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        await wild_event_callback(update, MagicMock())
    query.answer.assert_called_once()
    assert "caught" in query.answer.call_args[0][0].lower()
    query.edit_message_text.assert_called_once()
