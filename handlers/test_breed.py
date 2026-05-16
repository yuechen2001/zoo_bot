import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.breed import breed_command


def _make_update(args=None):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args or []
    return update, ctx


def _make_user(coins=500):
    user = MagicMock()
    user.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "coins": coins,
            "user_id": 1,
        }.get(k)
    )
    return user


def _make_animal(animal_id, rarity="common", is_breeding=0):
    a = MagicMock()
    a.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "animal_id": animal_id,
            "rarity": rarity,
            "is_breeding": is_breeding,
            "nickname": None,
            "species_name": "Frog",
            "emoji": "🐸",
            "habitat": "woodland",
            "catch_cost": 20,
            "hunger": 80,
        }.get(k)
    )
    return a


# ── /breed status ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_status_no_breeding():
    update, ctx = _make_update(args=["status"])
    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_pending_breed", return_value=None
    ):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "No breeding in progress" in reply


@pytest.mark.asyncio
async def test_breed_status_shows_time_remaining():
    update, ctx = _make_update(args=["status"])
    future = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(hours=2, minutes=30)
    ).isoformat()

    pending = MagicMock()
    pending.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "parent_a": "a1",
            "parent_b": "a2",
            "ready_at": future,
        }.get(k)
    )

    parent = MagicMock()
    parent.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "nickname": None,
            "name": "Frog",
            "emoji": "🐸",
        }.get(k)
    )

    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_pending_breed", return_value=pending
    ), patch("handlers.breed.db.get_conn") as mock_conn:
        inner = MagicMock()
        inner.execute.return_value.fetchone.return_value = parent
        mock_conn.return_value.__enter__ = MagicMock(return_value=inner)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        await breed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "2h" in reply
    assert "remaining" in reply


@pytest.mark.asyncio
async def test_breed_status_shows_ready_when_past():
    update, ctx = _make_update(args=["status"])
    past = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=5)
    ).isoformat()

    pending = MagicMock()
    pending.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "parent_a": "a1",
            "parent_b": "a2",
            "ready_at": past,
        }.get(k)
    )

    parent = MagicMock()
    parent.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "nickname": None,
            "name": "Frog",
            "emoji": "🐸",
        }.get(k)
    )

    with patch("handlers.breed.db.get_user", return_value=_make_user()), patch(
        "handlers.breed.db.get_pending_breed", return_value=pending
    ), patch("handlers.breed.db.get_conn") as mock_conn:
        inner = MagicMock()
        inner.execute.return_value.fetchone.return_value = parent
        mock_conn.return_value.__enter__ = MagicMock(return_value=inner)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        await breed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "ready" in reply.lower()


# ── /breed usage ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breed_no_args_shows_usage():
    update, ctx = _make_update(args=[])
    with patch("handlers.breed.db.get_user", return_value=_make_user()):
        await breed_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "/breed 1 3" in reply
    assert "/breed status" in reply
    assert "/breed collect" in reply


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
