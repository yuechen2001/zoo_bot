import datetime
import sys
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.breed import (
    breed_command,
    _collect_breed,
    breed_p1_callback,
    breed_p2_callback,
    breed_cancel_callback,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _make_update(args=None):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock(user_data={})
    ctx.args = args or []
    return update, ctx


def _make_user(coins=500):
    return make_row(coins=coins, user_id=1)


def _make_animal(animal_id, rarity="common", is_breeding=0, caught_at=None):
    import datetime

    if caught_at is None:
        caught_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return make_row(
        animal_id=animal_id,
        rarity=rarity,
        is_breeding=is_breeding,
        caught_at=caught_at,
        nickname=None,
        species_name="Frog",
        emoji="🐸",
        habitat="woodland",
        catch_cost=20,
        hunger=80,
    )


# ── /breed status removed — status is now shown in /zoo ───────────────────────


@pytest.mark.asyncio
async def test_breed_status_arg_shows_picker():
    """Non-digit single arg shows picker (or 'need 2 animals' if not enough)."""
    update, ctx = _make_update(args=["status"])
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_pending_breed", return_value=None
    ), patch("handlers.breed.db.get_animals", return_value=[_make_animal("a1")]):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "2" in reply or "breed" in reply.lower()


# ── /breed usage ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_no_args_shows_picker():
    update, ctx = _make_update(args=[])
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_pending_breed", return_value=None
    ), patch("handlers.breed.db.get_animals", return_value=[_make_animal("a1")]):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "2" in reply or "breed" in reply.lower()


@pytest.mark.asyncio
async def test_breed_rejects_unknown_user():
    update, ctx = _make_update(args=["1", "2"])
    with patch("handlers.breed.db.get_user", return_value=None):
        await breed_command(update, ctx)
    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_breed_rejects_same_position():
    update, ctx = _make_update(args=["1", "1"])
    with patch("handlers.breed.db.get_user", return_value=_make_user()):
        await breed_command(update, ctx)
    update.message.reply_text.assert_called_once_with("Pick two different animals!")


# ── /breed <a> <b> happy path ─────────────────────────────────────────────────


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, inner


@pytest.mark.asyncio
async def test_breed_starts_successfully():
    update, ctx = _make_update(args=["1", "2"])
    animal_a = _make_animal("a1", rarity="common")
    animal_b = _make_animal("a2", rarity="rare")

    cm, _ = _make_conn_mock()
    with patch("handlers.breed.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.breed.db.get_animal_by_position", side_effect=[animal_a, animal_b]
    ), patch("handlers.breed.db.get_pending_breed", return_value=None), patch(
        "handlers.breed.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.breed.db.get_conn", return_value=cm
    ), patch(
        "handlers.breed.resolve_offspring", return_value=1
    ), patch(
        "handlers.breed.calc_breed_ready_at", return_value="2099-01-01T00:00:00"
    ):
        await breed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "breeding" in reply.lower()
    assert "/breed collect" in reply


@pytest.mark.asyncio
async def test_breed_rejects_insufficient_coins():
    update, ctx = _make_update(args=["1", "2"])
    animal_a = _make_animal("a1", rarity="common")
    animal_b = _make_animal("a2", rarity="common")

    with patch("handlers.breed.db.get_user", return_value=_make_user(coins=5)), patch(
        "handlers.breed.db.get_animal_by_position", side_effect=[animal_a, animal_b]
    ), patch("handlers.breed.db.get_pending_breed", return_value=None), patch(
        "handlers.breed.db.get_enclosure_level", return_value=1
    ):
        await breed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "not enough coins" in reply.lower()


@pytest.mark.asyncio
async def test_breed_rejects_already_breeding():
    update, ctx = _make_update(args=["1", "2"])
    animal_a = _make_animal("a1")
    animal_b = _make_animal("a2")
    pending = make_row(id=1, ready_at="2099-01-01T00:00:00")

    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_animal_by_position", side_effect=[animal_a, animal_b]
    ), patch("handlers.breed.db.get_pending_breed", return_value=pending):
        await breed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "already have a breeding" in reply.lower()


# ── /breed collect ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_collect_nothing_pending():
    update, ctx = _make_update(args=["collect"])
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_pending_breed", return_value=None
    ):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "no breeding in progress" in reply.lower()


@pytest.mark.asyncio
async def test_breed_collect_not_ready():
    future = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(hours=2)
    ).isoformat()
    pending = make_row(id=1, ready_at=future, parent_a="a1", parent_b="a2")

    update, ctx = _make_update(args=["collect"])
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_pending_breed", return_value=pending
    ):
        await breed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "not ready" in reply.lower()


@pytest.mark.asyncio
async def test_breed_collect_ready():
    past = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=1)
    ).isoformat()
    pending = make_row(id=1, ready_at=past, parent_a="a1", parent_b="a2", offspring_species_id=1)
    species = make_row(species_id=1, name="Dragon", emoji="🐉", habitat="woodland")

    cm, _ = _make_conn_mock()
    update = MagicMock()
    update.message.reply_text = AsyncMock()

    with patch("handlers.breed.db.get_pending_breed", return_value=pending), patch(
        "handlers.breed.db.get_species", return_value=species
    ), patch("handlers.breed.db.get_enclosure_level", return_value=1), patch(
        "handlers.breed.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.breed.db.get_conn", return_value=cm
    ), patch(
        "handlers.breed.check_achievements"
    ):
        await _collect_breed(update, 1, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "hatched" in reply.lower() or "dragon" in reply.lower()


@pytest.mark.asyncio
async def test_breed_collect_blocked_when_enclosure_full():
    past = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=1)
    ).isoformat()
    pending = make_row(id=1, ready_at=past, parent_a="a1", parent_b="a2", offspring_species_id=1)
    species = make_row(species_id=1, name="Dragon", emoji="🐉", habitat="woodland")

    update = MagicMock()
    update.message.reply_text = AsyncMock()

    with patch("handlers.breed.db.get_pending_breed", return_value=pending), patch(
        "handlers.breed.db.get_species", return_value=species
    ), patch("handlers.breed.db.get_enclosure_level", return_value=1), patch(
        "handlers.breed.db.get_animal_count_by_habitat", return_value=3
    ):  # capacity 3 at level 1 → full
        await _collect_breed(update, 1, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "full" in reply.lower()


# ── breed_p1/p2 callbacks ─────────────────────────────────────────────────────


def _make_callback(user_id=1, data="breed_p1_1"):
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
async def test_breed_p1_shows_second_picker():
    update, query, ctx = _make_callback(data="breed_p1_1")
    animal_a = _make_animal("a1")
    animals = [animal_a, _make_animal("a2")]
    with patch("handlers.breed.db.get_pending_breed", return_value=None), patch(
        "handlers.breed.db.get_animal_by_position", return_value=animal_a
    ), patch("handlers.breed.db.get_animals", return_value=animals):
        await breed_p1_callback(update, ctx)
    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args[0][0]
    assert "parent 1" in text.lower() or "parent 2" in text.lower()


@pytest.mark.asyncio
async def test_breed_p1_blocked_when_already_breeding():
    update, query, ctx = _make_callback(data="breed_p1_1")
    pending = make_row(id=1, ready_at="2099-01-01T00:00:00")
    with patch("handlers.breed.db.get_pending_breed", return_value=pending):
        await breed_p1_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_breed_p2_starts_breed():
    update, query, ctx = _make_callback(data="breed_p2_1_2")
    animal_a = _make_animal("a1", rarity="common")
    animal_b = _make_animal("a2", rarity="common")
    cm, _ = _make_conn_mock()
    with patch("handlers.breed.db.get_user", return_value=_make_user(coins=500)), patch(
        "handlers.breed.db.get_animal_by_position", side_effect=[animal_a, animal_b]
    ), patch("handlers.breed.db.get_pending_breed", return_value=None), patch(
        "handlers.breed.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.breed.db.get_conn", return_value=cm
    ), patch(
        "handlers.breed.resolve_offspring", return_value=1
    ), patch(
        "handlers.breed.calc_breed_ready_at", return_value="2099-01-01T00:00:00"
    ), patch(
        "handlers.breed.check_achievements"
    ):
        await breed_p2_callback(update, ctx)
    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args[0][0]
    assert "breeding" in text.lower()


@pytest.mark.asyncio
async def test_breed_cancel_dismisses():
    update, query, ctx = _make_callback(data="breed_cancel")
    await breed_cancel_callback(update, ctx)
    query.answer.assert_called_once_with("Cancelled")
    query.edit_message_text.assert_called_once_with("Breed cancelled.")


@pytest.mark.asyncio
async def test_breed_no_args_shows_in_progress_when_pending():
    update, ctx = _make_update(args=[])
    pending = make_row(id=1, ready_at="2099-01-01T00:00:00")
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_pending_breed", return_value=pending
    ):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "already have a breeding" in reply.lower()


@pytest.mark.asyncio
async def test_breed_invalid_positions():
    update, ctx = _make_update(args=["1", "99"])
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_animal_by_position", return_value=None
    ), patch("handlers.breed.db.get_animals", return_value=[_make_animal("a1")]):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "invalid" in reply.lower() or "animal" in reply.lower()


@pytest.mark.asyncio
async def test_breed_one_already_breeding():
    update, ctx = _make_update(args=["1", "2"])
    animal_a = _make_animal("a1", is_breeding=1)
    animal_b = _make_animal("a2")
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_animal_by_position", side_effect=[animal_a, animal_b]
    ), patch("handlers.breed.db.get_pending_breed", return_value=None):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "already breeding" in reply.lower()


# ── breed_p1_callback edge cases ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_p1_animal_not_found():
    update, query, ctx = _make_callback(data="breed_p1_5")
    with patch("handlers.breed.db.get_pending_breed", return_value=None), patch(
        "handlers.breed.db.get_animal_by_position", return_value=None
    ):
        await breed_p1_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_breed_p1_animal_is_breeding():
    update, query, ctx = _make_callback(data="breed_p1_1")
    animal = _make_animal("a1", is_breeding=1)
    with patch("handlers.breed.db.get_pending_breed", return_value=None), patch(
        "handlers.breed.db.get_animal_by_position", return_value=animal
    ):
        await breed_p1_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


# ── breed_p2_callback edge cases ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_p2_animals_not_found():
    update, query, ctx = _make_callback(data="breed_p2_1_2")
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_animal_by_position", return_value=None
    ):
        await breed_p2_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_breed_p2_one_is_breeding():
    update, query, ctx = _make_callback(data="breed_p2_1_2")
    animal_a = _make_animal("a1", is_breeding=1)
    animal_b = _make_animal("a2")
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_animal_by_position", side_effect=[animal_a, animal_b]
    ):
        await breed_p2_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True


@pytest.mark.asyncio
async def test_breed_p2_insufficient_coins():
    update, query, ctx = _make_callback(data="breed_p2_1_2")
    animal_a = _make_animal("a1", rarity="legendary")
    animal_b = _make_animal("a2", rarity="legendary")
    with patch("handlers.breed.db.get_user", return_value=_make_user(coins=5)), patch(
        "handlers.breed.db.get_animal_by_position", side_effect=[animal_a, animal_b]
    ), patch("handlers.breed.db.get_pending_breed", return_value=None):
        await breed_p2_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True


# ── breed_page_callback ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_page_callback_already_breeding():
    from handlers.breed import breed_page_callback

    update, query, ctx = _make_callback(data="breed_page_1")
    pending = make_row(id=1, ready_at="2099-01-01T00:00:00")
    with patch("handlers.breed.db.get_pending_breed", return_value=pending):
        await breed_page_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_breed_page_callback_shows_picker():
    from handlers.breed import breed_page_callback

    update, query, ctx = _make_callback(data="breed_page_0")
    animals = [_make_animal("a1"), _make_animal("a2")]
    with patch("handlers.breed.db.get_pending_breed", return_value=None), patch(
        "handlers.breed.db.get_animals", return_value=animals
    ):
        await breed_page_callback(update, ctx)
    query.edit_message_text.assert_called_once()


# ── breed_p2_page_callback ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_p2_page_callback_animal_not_found():
    from handlers.breed import breed_p2_page_callback

    update, query, ctx = _make_callback(data="breed_p2_page_1_0")
    with patch("handlers.breed.db.get_animal_by_position", return_value=None):
        await breed_p2_page_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_breed_p2_page_callback_shows_picker():
    from handlers.breed import breed_p2_page_callback

    update, query, ctx = _make_callback(data="breed_p2_page_1_0")
    animal_a = _make_animal("a1")
    animals = [animal_a, _make_animal("a2")]
    with patch("handlers.breed.db.get_animal_by_position", return_value=animal_a), patch(
        "handlers.breed.db.get_animals", return_value=animals
    ):
        await breed_p2_page_callback(update, ctx)
    query.edit_message_text.assert_called_once()
