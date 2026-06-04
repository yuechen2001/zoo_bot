import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.escape import escape_callback


def _make_query(escape_id: int, action: str, user_id: int = 1):
    query = MagicMock()
    query.data = f"escape_{escape_id}_{action}"
    query.from_user.id = user_id
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


def _make_escape(
    escape_id: int = 1,
    user_id: int = 1,
    animal_id: str = "abc",
    resolved: int = 0,
    expires_offset_hours: float = 1.0,
):
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    expires = (now + datetime.timedelta(hours=expires_offset_hours)).isoformat()
    e = MagicMock()
    e.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "escape_id": escape_id,
            "user_id": user_id,
            "animal_id": animal_id,
            "resolved": resolved,
            "expires_at": expires,
            "group_chat_id": -100,
            "message_id": 42,
        }[k]
    )
    return e


def _make_animal(animal_id: str = "abc", habitat: str = "woodland", catch_cost: int = 20):
    a = MagicMock()
    a.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "animal_id": animal_id,
            "nickname": None,
            "species_name": "Fox",
            "emoji": "🦊",
            "habitat": habitat,
            "catch_cost": catch_cost,
            "hunger": 80,
        }[k]
    )
    return a


# ── guard checks ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_escape_rejects_unknown_user():
    query = _make_query(1, "chase")
    update = MagicMock()
    update.callback_query = query

    with patch("handlers.escape.db.get_user", return_value=None):
        await escape_callback(update, MagicMock())

    query.answer.assert_called_once_with("Use /start first!", show_alert=True)


@pytest.mark.asyncio
async def test_escape_rejects_wrong_owner():
    query = _make_query(1, "chase", user_id=99)
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape(user_id=1)  # owner is 1, caller is 99

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ):
        await escape_callback(update, MagicMock())

    query.answer.assert_called_once_with("This isn't your animal!", show_alert=True)


@pytest.mark.asyncio
async def test_escape_rejects_already_resolved():
    query = _make_query(1, "chase")
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape(resolved=1)

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ):
        await escape_callback(update, MagicMock())

    query.answer.assert_called_once_with("This escape event is already over.", show_alert=True)


@pytest.mark.asyncio
async def test_escape_rejects_expired_window():
    query = _make_query(1, "chase")
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape(expires_offset_hours=-1.0)  # expired 1h ago

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ):
        await escape_callback(update, MagicMock())

    query.answer.assert_called_once_with("Time's up — the window has closed!", show_alert=True)


# ── chase action ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chase_success_resolves_escape():
    query = _make_query(1, "chase")
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape()
    animal = _make_animal()

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ), patch("handlers.escape.db.get_animal", return_value=animal), patch(
        "handlers.escape.db.resolve_escape"
    ) as mock_resolve, patch(
        "handlers.escape.random.random", return_value=0.1
    ):  # 0.1 < 0.35 → success
        await escape_callback(update, MagicMock())

    mock_resolve.assert_called_once_with(1, 1)
    query.edit_message_text.assert_called_once()
    assert (
        "chased" in query.edit_message_text.call_args[0][0].lower()
        or "resolved" in query.edit_message_text.call_args[0][0].lower()
    )


@pytest.mark.asyncio
async def test_chase_failure_deletes_animal():
    query = _make_query(1, "chase")
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape()
    animal = _make_animal()

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ), patch("handlers.escape.db.get_animal", return_value=animal), patch(
        "handlers.escape.db.resolve_escape"
    ) as mock_resolve, patch(
        "handlers.escape.db.delete_animal"
    ) as mock_delete, patch(
        "handlers.escape.random.random", return_value=0.9
    ):  # 0.9 > 0.35 → failure
        await escape_callback(update, MagicMock())

    mock_delete.assert_called_once_with("abc")
    mock_resolve.assert_called_once_with(1, 2)


# ── release action ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_release_awards_refund_and_deletes():
    query = _make_query(1, "release")
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape()
    animal = _make_animal(catch_cost=20)  # sell base = 10, refund = round(10 * 0.30) = 3

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ), patch("handlers.escape.db.get_animal", return_value=animal), patch(
        "handlers.escape.db.add_coins"
    ) as mock_add, patch(
        "handlers.escape.db.delete_animal"
    ) as mock_delete, patch(
        "handlers.escape.db.resolve_escape"
    ) as mock_resolve:
        await escape_callback(update, MagicMock())

    mock_add.assert_called_once_with(1, 3)
    mock_delete.assert_called_once_with("abc")
    mock_resolve.assert_called_once_with(1, 3)


# ── lure action ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lure_no_item_rejects():
    query = _make_query(1, "lure")
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape()
    animal = _make_animal(habitat="woodland")

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ), patch("handlers.escape.db.get_animal", return_value=animal), patch(
        "handlers.escape.db.get_oldest_purchase", return_value=None
    ):
        await escape_callback(update, MagicMock())

    query.answer.assert_called_once()
    assert "lure" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_lure_success_resolves_escape():
    query = _make_query(1, "lure")
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape()
    animal = _make_animal(habitat="woodland")
    purchase = MagicMock()
    purchase.__getitem__ = MagicMock(side_effect=lambda k: 7 if k == "id" else None)

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ), patch("handlers.escape.db.get_animal", return_value=animal), patch(
        "handlers.escape.db.get_oldest_purchase", return_value=purchase
    ), patch(
        "handlers.escape.db.consume_purchase"
    ) as mock_consume, patch(
        "handlers.escape.db.resolve_escape"
    ) as mock_resolve, patch(
        "handlers.escape.random.random", return_value=0.05
    ):  # 0.05 < 0.90 → success
        await escape_callback(update, MagicMock())

    mock_consume.assert_called_once_with(7)
    mock_resolve.assert_called_once_with(1, 1)


@pytest.mark.asyncio
async def test_lure_failure_deletes_animal():
    query = _make_query(1, "lure")
    update = MagicMock()
    update.callback_query = query

    escape = _make_escape()
    animal = _make_animal(habitat="woodland")
    purchase = MagicMock()
    purchase.__getitem__ = MagicMock(side_effect=lambda k: 7 if k == "id" else None)

    with patch("handlers.escape.db.get_user", return_value={"coins": 100}), patch(
        "handlers.escape.db.get_escape", return_value=escape
    ), patch("handlers.escape.db.get_animal", return_value=animal), patch(
        "handlers.escape.db.get_oldest_purchase", return_value=purchase
    ), patch(
        "handlers.escape.db.consume_purchase"
    ), patch(
        "handlers.escape.db.delete_animal"
    ) as mock_delete, patch(
        "handlers.escape.db.resolve_escape"
    ) as mock_resolve, patch(
        "handlers.escape.random.random", return_value=0.95
    ):  # 0.95 > 0.90 → failure
        await escape_callback(update, MagicMock())

    mock_delete.assert_called_once_with("abc")
    mock_resolve.assert_called_once_with(1, 2)
