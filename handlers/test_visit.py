import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.visit import visit_command, visit_feed_callback
from game.constants import VISIT_FEED_COOLDOWN_HOURS, VISIT_FEED_BONUS, FEED_HUNGER


def _make_user(user_id=1, coins=100):
    u = MagicMock()
    u.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "user_id": user_id,
            "username": "alice",
            "coins": coins,
            "group_chat_id": -100,
        }[k]
    )
    return u


def _make_animal(animal_id="a1", hunger=60, rarity="common"):
    a = MagicMock()
    a.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "animal_id": animal_id,
            "nickname": None,
            "species_name": "Fox",
            "species_id": 1,
            "emoji": "🦊",
            "habitat": "woodland",
            "rarity": rarity,
            "hunger": hunger,
        }[k]
    )
    return a


def _recent_feed_row(hours_ago: float = 1.0):
    fed_at = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
    ).isoformat()
    r = MagicMock()
    r.__getitem__ = MagicMock(side_effect=lambda k: fed_at if k == "fed_at" else None)
    return r


# ── visit_command ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_visit_rejects_unregistered_visitor():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    with patch("handlers.visit.db.get_user", return_value=None):
        await visit_command(update, MagicMock())

    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_visit_requires_username_arg():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock(user_data={})
    ctx.args = []

    with patch("handlers.visit.db.get_user", return_value=_make_user()):
        await visit_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "usage" in reply.lower() or "/visit" in reply.lower()


@pytest.mark.asyncio
async def test_visit_rejects_unknown_host():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock(user_data={})
    ctx.args = ["@nobody"]

    with patch("handlers.visit.db.get_user", return_value=_make_user()), patch(
        "handlers.visit.db.get_user_by_username", return_value=None
    ):
        await visit_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "not found" in reply.lower()


@pytest.mark.asyncio
async def test_visit_rejects_self():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock(user_data={})
    ctx.args = ["alice"]

    with patch("handlers.visit.db.get_user", return_value=_make_user(user_id=1)), patch(
        "handlers.visit.db.get_user_by_username", return_value=_make_user(user_id=1)
    ):
        await visit_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "own" in reply.lower() or "yourself" in reply.lower() or "/zoo" in reply


@pytest.mark.asyncio
async def test_visit_shows_feed_button_when_eligible():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock(user_data={})
    ctx.args = ["bob"]

    host = _make_user(user_id=2)
    animals = [_make_animal()]

    with patch("handlers.visit.db.get_user", return_value=_make_user(user_id=1)), patch(
        "handlers.visit.db.get_user_by_username", return_value=host
    ), patch("handlers.visit.db.get_animals", return_value=animals), patch(
        "handlers.visit.db.get_last_visit_feed", return_value=None
    ):
        await visit_command(update, ctx)

    update.message.reply_text.assert_called_once()
    kb = update.message.reply_text.call_args[1]["reply_markup"]
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    assert any("visit_feed_2" in btn.callback_data for btn in buttons)


@pytest.mark.asyncio
async def test_visit_hides_feed_button_within_cooldown():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock(user_data={})
    ctx.args = ["bob"]

    host = _make_user(user_id=2)
    animals = [_make_animal()]

    with patch("handlers.visit.db.get_user", return_value=_make_user(user_id=1)), patch(
        "handlers.visit.db.get_user_by_username", return_value=host
    ), patch("handlers.visit.db.get_animals", return_value=animals), patch(
        "handlers.visit.db.get_last_visit_feed",
        return_value=_recent_feed_row(hours_ago=1.0),  # 1h ago, cooldown is 24h
    ):
        await visit_command(update, ctx)

    kb = update.message.reply_text.call_args[1]["reply_markup"]
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    assert not any("visit_feed_" in btn.callback_data for btn in buttons)


@pytest.mark.asyncio
async def test_visit_hides_feed_button_when_zoo_empty():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock(user_data={})
    ctx.args = ["bob"]

    host = _make_user(user_id=2)

    with patch("handlers.visit.db.get_user", return_value=_make_user(user_id=1)), patch(
        "handlers.visit.db.get_user_by_username", return_value=host
    ), patch("handlers.visit.db.get_animals", return_value=[]), patch(
        "handlers.visit.db.get_last_visit_feed", return_value=None
    ):
        await visit_command(update, ctx)

    kb = update.message.reply_text.call_args[1]["reply_markup"]
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    assert not any("visit_feed_" in btn.callback_data for btn in buttons)


# ── visit_feed_callback ────────────────────────────────────────────────────────


def _make_feed_query(host_id=2, user_id=1):
    query = MagicMock()
    query.from_user.id = user_id
    query.data = f"visit_feed_{host_id}"
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query


@pytest.mark.asyncio
async def test_visit_feed_rejects_unregistered_visitor():
    update, query = _make_feed_query()

    with patch("handlers.visit.db.get_user", return_value=None):
        await visit_feed_callback(update, MagicMock())

    query.answer.assert_called_once_with("Use /start first!", show_alert=True)


@pytest.mark.asyncio
async def test_visit_feed_enforces_cooldown():
    update, query = _make_feed_query()

    with patch("handlers.visit.db.get_user", return_value=_make_user()), patch(
        "handlers.visit.db.get_last_visit_feed",
        return_value=_recent_feed_row(hours_ago=1.0),  # 1h ago, still in 24h cooldown
    ):
        await visit_feed_callback(update, MagicMock())

    query.answer.assert_called_once()
    assert "cooldown" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_visit_feed_rejects_empty_zoo():
    update, query = _make_feed_query()

    with patch("handlers.visit.db.get_user", return_value=_make_user()), patch(
        "handlers.visit.db.get_last_visit_feed", return_value=None
    ), patch("handlers.visit.db.get_animals", return_value=[]):
        await visit_feed_callback(update, MagicMock())

    query.answer.assert_called_once_with("Their zoo is empty!", show_alert=True)


@pytest.mark.asyncio
async def test_visit_feed_rejects_fully_fed_zoo():
    update, query = _make_feed_query()
    full_animal = _make_animal(hunger=100)

    with patch("handlers.visit.db.get_user", return_value=_make_user()), patch(
        "handlers.visit.db.get_last_visit_feed", return_value=None
    ), patch("handlers.visit.db.get_animals", return_value=[full_animal]):
        await visit_feed_callback(update, MagicMock())

    query.answer.assert_called_once_with("All animals are fully fed already!", show_alert=True)


@pytest.mark.asyncio
async def test_visit_feed_rejects_insufficient_visitor_coins():
    update, query = _make_feed_query()
    hungry = _make_animal(hunger=50, rarity="common")  # feed cost = 5 for common

    with patch("handlers.visit.db.get_user", return_value=_make_user(coins=0)), patch(
        "handlers.visit.db.get_last_visit_feed", return_value=None
    ), patch("handlers.visit.db.get_animals", return_value=[hungry]):
        await visit_feed_callback(update, MagicMock())

    query.answer.assert_called_once()
    assert "enough" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_visit_feed_feeds_hungriest_animal_and_awards_bonus():
    update, query = _make_feed_query()
    hungry = _make_animal(animal_id="a1", hunger=30, rarity="common")  # cost = 5

    with patch("handlers.visit.db.get_user", return_value=_make_user(coins=100)), patch(
        "handlers.visit.db.get_last_visit_feed", return_value=None
    ), patch("handlers.visit.db.get_animals", return_value=[hungry]), patch(
        "handlers.visit.db.feed_animal"
    ) as mock_feed, patch(
        "handlers.visit.db.add_coins"
    ) as mock_add, patch(
        "handlers.visit.db.record_visit_feed"
    ) as mock_record:
        await visit_feed_callback(update, MagicMock())

    mock_feed.assert_called_once_with(1, "a1", 30 + FEED_HUNGER, 5)
    mock_add.assert_called_once_with(1, VISIT_FEED_BONUS)
    mock_record.assert_called_once()
    query.edit_message_reply_markup.assert_called_once()


@pytest.mark.asyncio
async def test_visit_feed_allowed_after_cooldown_expires():
    """Feed button works once cooldown has passed."""
    update, query = _make_feed_query()
    hungry = _make_animal(hunger=50, rarity="common")

    old_feed = _recent_feed_row(hours_ago=VISIT_FEED_COOLDOWN_HOURS + 1)

    with patch("handlers.visit.db.get_user", return_value=_make_user(coins=100)), patch(
        "handlers.visit.db.get_last_visit_feed", return_value=old_feed
    ), patch("handlers.visit.db.get_animals", return_value=[hungry]), patch(
        "handlers.visit.db.feed_animal"
    ), patch(
        "handlers.visit.db.add_coins"
    ) as mock_add, patch(
        "handlers.visit.db.record_visit_feed"
    ):
        await visit_feed_callback(update, MagicMock())

    mock_add.assert_called_once_with(1, VISIT_FEED_BONUS)
