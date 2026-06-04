"""Tests for the /inspect command — animal stat display."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.inspect import inspect_command, _stars


# ── _stars helper ─────────────────────────────────────────────────────────────


def test_stars_zero():
    assert _stars(0) == "★☆☆☆☆"


def test_stars_mid():
    assert _stars(50) == "★★★☆☆"


def test_stars_max():
    assert _stars(100) == "★★★★★"


def test_stars_boundary_30():
    assert _stars(30) == "★★☆☆☆"


def test_stars_boundary_90():
    assert _stars(90) == "★★★★★"


# ── inspect_command ────────────────────────────────────────────────────────────


def _make_update(user_id=1, args=None):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    ctx = MagicMock(user_data={})
    ctx.args = args or []
    return update, ctx


@pytest.mark.asyncio
async def test_inspect_no_start():
    update, ctx = _make_update(args=["1"])
    with patch("handlers.inspect.db.get_user", return_value=None):
        await inspect_command(update, ctx)
    update.message.reply_text.assert_called_once()
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inspect_no_args():
    update, ctx = _make_update(args=[])
    with patch("handlers.inspect.db.get_user", return_value=MagicMock()):
        await inspect_command(update, ctx)
    update.message.reply_text.assert_called_once()
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_inspect_non_numeric_arg():
    update, ctx = _make_update(args=["abc"])
    with patch("handlers.inspect.db.get_user", return_value=MagicMock()):
        await inspect_command(update, ctx)
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_inspect_invalid_position():
    update, ctx = _make_update(args=["99"])
    with patch("handlers.inspect.db.get_user", return_value=MagicMock()), patch(
        "handlers.inspect.db.get_animal_by_position", return_value=None
    ), patch("handlers.inspect.db.get_animals", return_value=[]):
        await inspect_command(update, ctx)
    assert "No animal" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_inspect_shows_stats():
    from conftest import make_row

    animal = make_row(
        animal_id="abc",
        species_name="Fox",
        nickname=None,
        emoji="🦊",
        stat_speed=70,
        stat_rarity=40,
        stat_temperament=90,
    )
    update, ctx = _make_update(args=["1"])
    with patch("handlers.inspect.db.get_user", return_value=MagicMock()), patch(
        "handlers.inspect.db.get_animal_by_position", return_value=animal
    ):
        await inspect_command(update, ctx)

    text = update.message.reply_text.call_args[0][0]
    assert "Fox" in text
    assert "Speed" in text
    assert "Genetics" in text
    assert "Temperament" in text
    # stat_speed=70 → 4 stars; stat_rarity=40 → 2 stars; stat_temperament=90 → 5 stars
    assert "★★★★" in text
