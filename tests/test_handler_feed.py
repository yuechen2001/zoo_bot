import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.feed import feed_command, FEED_COST, FEED_HUNGER


def _make_animal(name="Mouse", emoji="🐭", is_breeding=0, hunger=50, nickname=None):
    return {
        "animal_id": "a1",
        "nickname": nickname,
        "species_name": name,
        "emoji": emoji,
        "is_breeding": is_breeding,
        "hunger": hunger,
    }


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


# ── Fix 4: multi-animal feed ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_feed_no_args_shows_usage():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.args = []

    with patch("handlers.feed.db.get_user", return_value={"coins": 100}):
        await feed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply or "usage" in reply


@pytest.mark.asyncio
async def test_feed_happy_path_single_animal():
    animal = _make_animal(name="Buddy", nickname="Buddy", hunger=40)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.args = ["1"]

    with patch("handlers.feed.db.get_user", return_value={"coins": 100}), patch(
        "handlers.feed.db.get_animal_by_position", return_value=animal
    ), patch("handlers.feed.db.get_conn", return_value=_make_conn_mock()):
        await feed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "Buddy" in reply
    assert f"40→{min(100, 40 + FEED_HUNGER)}" in reply


@pytest.mark.asyncio
async def test_feed_skips_breeding_animal():
    animal = _make_animal(name="Cat", emoji="🐱", is_breeding=1)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.args = ["1"]

    with patch("handlers.feed.db.get_user", return_value={"coins": 100}), patch(
        "handlers.feed.db.get_animal_by_position", return_value=animal
    ):
        await feed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "breeding" in reply.lower()


@pytest.mark.asyncio
async def test_feed_stops_when_coins_run_out():
    """Fix 4: loop must break (not continue) when coins are exhausted mid-feed."""
    animal = _make_animal()

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.args = ["1", "2"]

    # initial check → has user; loop iter #1 → 10 coins (enough); loop iter #2 → 0 coins (break)
    users = [{"coins": 100}, {"coins": FEED_COST}, {"coins": 0}]

    with patch("handlers.feed.db.get_user", side_effect=users), patch(
        "handlers.feed.db.get_animal_by_position", return_value=animal
    ), patch("handlers.feed.db.get_conn", return_value=_make_conn_mock()):
        await feed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "not enough coins" in reply
    # First animal was successfully fed (shows 🍖)
    assert "🍖" in reply


@pytest.mark.asyncio
async def test_feed_missing_position_shows_not_found():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.args = ["99"]

    with patch("handlers.feed.db.get_user", return_value={"coins": 100}), patch(
        "handlers.feed.db.get_animal_by_position", return_value=None
    ):
        await feed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "no animal found" in reply


@pytest.mark.asyncio
async def test_feed_hunger_capped_at_100():
    animal = _make_animal(hunger=90)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.args = ["1"]

    with patch("handlers.feed.db.get_user", return_value={"coins": 100}), patch(
        "handlers.feed.db.get_animal_by_position", return_value=animal
    ), patch("handlers.feed.db.get_conn", return_value=_make_conn_mock()):
        await feed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "90→100" in reply  # hunger: 90 + 40 capped at 100


@pytest.mark.asyncio
async def test_feed_blocked_when_already_full():
    animal = _make_animal(hunger=100)

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.args = ["1"]

    with patch("handlers.feed.db.get_user", return_value={"coins": 100}), patch(
        "handlers.feed.db.get_animal_by_position", return_value=animal
    ):
        await feed_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "full" in reply.lower()
    # No coin deduction should happen
    assert "🍖" not in reply
