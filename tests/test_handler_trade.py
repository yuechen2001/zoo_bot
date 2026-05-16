import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.trade import trade_command, trade_callback


def _make_update(user_id=1, username="alice", first_name="Alice"):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_user.first_name = first_name
    update.message.reply_text = AsyncMock()
    return update


def _make_ctx(args=None):
    ctx = MagicMock()
    ctx.args = args or []
    return ctx


def _make_animal(animal_id="a1", rarity="common", is_breeding=0, nickname="Mouse", emoji="🐭"):
    return {
        "animal_id": animal_id,
        "species_name": "Mouse",
        "nickname": nickname,
        "emoji": emoji,
        "rarity": rarity,
        "is_breeding": is_breeding,
    }


def _make_user(user_id=2, username="bob"):
    return {"user_id": user_id, "username": username}


def _make_query(action="accept", trade_id=1, recipient_id=2, from_user_id=2):
    query = MagicMock()
    query.data = f"trade_{action}_{trade_id}_{recipient_id}"
    query.from_user.id = from_user_id
    query.from_user.username = "bob"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query


# ── trade_command ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trade_rejects_missing_args():
    update = _make_update()
    ctx = _make_ctx(args=[])
    with patch("handlers.trade.db.get_user", return_value=_make_user(1, "alice")):
        await trade_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply


@pytest.mark.asyncio
async def test_trade_rejects_unknown_user():
    update = _make_update()
    ctx = _make_ctx(args=["@nobody", "1", "1"])
    with patch("handlers.trade.db.get_user", return_value=_make_user(1, "alice")), patch(
        "handlers.trade.db.get_user_by_username", return_value=None
    ):
        await trade_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "nobody" in reply or "started" in reply


@pytest.mark.asyncio
async def test_trade_rejects_self_trade():
    update = _make_update(user_id=1)
    ctx = _make_ctx(args=["@alice", "1", "1"])
    with patch("handlers.trade.db.get_user", return_value=_make_user(1, "alice")), patch(
        "handlers.trade.db.get_user_by_username", return_value=_make_user(1, "alice")
    ):
        await trade_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "yourself" in reply


@pytest.mark.asyncio
async def test_trade_rejects_breeding_proposer_animal():
    update = _make_update(user_id=1)
    ctx = _make_ctx(args=["@bob", "1", "1"])
    with patch("handlers.trade.db.get_user", return_value=_make_user(1, "alice")), patch(
        "handlers.trade.db.get_user_by_username", return_value=_make_user(2, "bob")
    ), patch(
        "handlers.trade.db.get_animal_by_position",
        side_effect=[_make_animal(is_breeding=1), _make_animal(animal_id="b1")],
    ):
        await trade_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "breeding" in reply.lower()


@pytest.mark.asyncio
async def test_trade_sends_proposal_with_keyboard():
    update = _make_update(user_id=1)
    ctx = _make_ctx(args=["@bob", "1", "1"])
    with patch("handlers.trade.db.get_user", return_value=_make_user(1, "alice")), patch(
        "handlers.trade.db.get_user_by_username", return_value=_make_user(2, "bob")
    ), patch(
        "handlers.trade.db.get_animal_by_position",
        side_effect=[_make_animal(animal_id="a1"), _make_animal(animal_id="b1")],
    ), patch(
        "handlers.trade.db.has_pending_trade_for_animal", return_value=False
    ), patch(
        "handlers.trade.db.create_trade", return_value=42
    ), patch(
        "handlers.trade.trade_keyboard", return_value=MagicMock()
    ) as mock_kb:
        await trade_command(update, ctx)
    mock_kb.assert_called_once_with(42, 2)
    update.message.reply_text.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "Trade Proposal" in reply or "trade" in reply.lower()


# ── trade_callback ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trade_callback_rejects_wrong_user():
    update, query = _make_query(action="accept", trade_id=1, recipient_id=2, from_user_id=99)
    await trade_callback(update, MagicMock())
    query.answer.assert_called_once_with("This isn't your trade!", show_alert=True)


@pytest.mark.asyncio
async def test_trade_callback_accept_calls_resolve():
    update, query = _make_query(action="accept", trade_id=1, recipient_id=2, from_user_id=2)
    now = datetime.datetime.utcnow().isoformat()
    trade = {
        "id": 1,
        "status": "pending",
        "created_at": now,
        "proposer_animal_id": "a1",
        "recipient_animal_id": "b1",
    }
    with patch("handlers.trade.db.get_trade", return_value=trade), patch(
        "handlers.trade.db.resolve_trade"
    ) as mock_resolve, patch(
        "handlers.trade.db.get_animal",
        side_effect=[_make_animal("a1"), _make_animal("b1")],
    ):
        await trade_callback(update, MagicMock())
    mock_resolve.assert_called_once_with(1, "accepted")
    query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_trade_callback_decline_calls_resolve():
    update, query = _make_query(action="decline", trade_id=1, recipient_id=2, from_user_id=2)
    now = datetime.datetime.utcnow().isoformat()
    trade = {
        "id": 1,
        "status": "pending",
        "created_at": now,
        "proposer_animal_id": "a1",
        "recipient_animal_id": "b1",
    }
    with patch("handlers.trade.db.get_trade", return_value=trade), patch(
        "handlers.trade.db.resolve_trade"
    ) as mock_resolve, patch(
        "handlers.trade.db.get_animal",
        side_effect=[_make_animal("a1"), _make_animal("b1")],
    ):
        await trade_callback(update, MagicMock())
    mock_resolve.assert_called_once_with(1, "declined")


@pytest.mark.asyncio
async def test_trade_callback_expired_trade():
    update, query = _make_query(action="accept", trade_id=1, recipient_id=2, from_user_id=2)
    old_time = (datetime.datetime.utcnow() - datetime.timedelta(minutes=15)).isoformat()
    trade = {
        "id": 1,
        "status": "pending",
        "created_at": old_time,
        "proposer_animal_id": "a1",
        "recipient_animal_id": "b1",
    }
    with patch("handlers.trade.db.get_trade", return_value=trade), patch(
        "handlers.trade.db.resolve_trade"
    ) as mock_resolve:
        await trade_callback(update, MagicMock())
    mock_resolve.assert_called_once_with(1, "declined")
    reply = query.edit_message_text.call_args[0][0]
    assert "expired" in reply.lower()


@pytest.mark.asyncio
async def test_trade_callback_already_resolved():
    update, query = _make_query(action="accept", trade_id=1, recipient_id=2, from_user_id=2)
    trade = {"id": 1, "status": "accepted", "created_at": datetime.datetime.utcnow().isoformat()}
    with patch("handlers.trade.db.get_trade", return_value=trade):
        await trade_callback(update, MagicMock())
    query.answer.assert_called_once_with("This trade is no longer active.")
