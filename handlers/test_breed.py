import datetime
import sys
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.breed import breed_command, _collect_breed

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _make_update(args=None):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args or []
    return update, ctx


def _make_user(coins=500):
    return make_row(coins=coins, user_id=1)


def _make_animal(animal_id, rarity="common", is_breeding=0):
    return make_row(
        animal_id=animal_id,
        rarity=rarity,
        is_breeding=is_breeding,
        nickname=None,
        species_name="Frog",
        emoji="🐸",
        habitat="woodland",
        catch_cost=20,
        hunger=80,
    )


# ── /breed status removed — status is now shown in /zoo ───────────────────────


@pytest.mark.asyncio
async def test_breed_status_arg_shows_usage():
    """/breed status no longer exists — should show usage hint pointing to /zoo."""
    update, ctx = _make_update(args=["status"])
    with patch("handlers.breed.db.get_user", return_value=_make_user()):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "/zoo" in reply


# ── /breed usage ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_no_args_shows_usage():
    update, ctx = _make_update(args=[])
    with patch("handlers.breed.db.get_user", return_value=_make_user()):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "/breed 1 3" in reply
    assert "/breed collect" in reply
    assert "/zoo" in reply


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
    species = make_row(species_id=1, name="Dragon", emoji="🐉")

    cm, _ = _make_conn_mock()
    update = MagicMock()
    update.message.reply_text = AsyncMock()

    with patch("handlers.breed.db.get_pending_breed", return_value=pending), patch(
        "handlers.breed.db.get_species", return_value=species
    ), patch("handlers.breed.db.get_conn", return_value=cm), patch(
        "handlers.breed.check_achievements"
    ):
        await _collect_breed(update, 1, MagicMock())

    reply = update.message.reply_text.call_args[0][0]
    assert "hatched" in reply.lower() or "dragon" in reply.lower()
