import sys
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.breed import breed_command

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
