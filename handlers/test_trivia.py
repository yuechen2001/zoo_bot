import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.trivia import (
    trivia_command,
    trivia_callback,
    TRIVIA_COOLDOWN_MINUTES,
    COINS_CORRECT,
    COINS_WRONG,
)


def _make_conn_mock(last_asked=None):
    """Return a mock context manager whose execute().fetchone() returns the given row."""
    inner = MagicMock()
    row = MagicMock()
    row.__getitem__ = MagicMock(side_effect=lambda k: last_asked if k == "asked_at" else None)
    inner.execute.return_value.fetchone.return_value = row if last_asked else None
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, inner


def _make_trivia_query(user_id: int, option: str = "B"):
    query = MagicMock()
    query.data = f"trivia_{user_id}_{option}"
    query.from_user.id = user_id
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


# ── trivia_command ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trivia_rejects_unknown_user():
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()

    with patch("handlers.trivia.db.get_user", return_value=None), patch(
        "handlers.trivia.db.get_conn", return_value=_make_conn_mock()[0]
    ):
        await trivia_command(update, ctx)

    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_trivia_cooldown_blocks_early_repeat():
    recent = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=5)
    ).isoformat()
    cm, _ = _make_conn_mock(last_asked=recent)

    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()

    with patch("handlers.trivia.db.get_user", return_value={"coins": 100}), patch(
        "handlers.trivia.db.get_conn", return_value=cm
    ):
        await trivia_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "min" in reply or "Next trivia" in reply


@pytest.mark.asyncio
async def test_trivia_starts_after_cooldown():
    old = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=TRIVIA_COOLDOWN_MINUTES + 1)
    ).isoformat()
    cm, inner = _make_conn_mock(last_asked=old)

    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.user_data = {}

    with patch("handlers.trivia.db.get_user", return_value={"coins": 100}), patch(
        "handlers.trivia.db.get_conn", return_value=cm
    ), patch(
        "handlers.trivia.random.choice",
        return_value={
            "q": "What animal is fastest?",
            "options": ["A) Cat", "B) Cheetah", "C) Horse", "D) Dog"],
            "answer": "B",
        },
    ):
        await trivia_command(update, ctx)

    update.message.reply_text.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "Trivia" in reply or "trivia" in reply.lower()
    assert ctx.user_data.get("trivia") is not None


# ── trivia_callback ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trivia_callback_rejects_wrong_user():
    query = _make_trivia_query(user_id=123)
    query.from_user.id = 456  # different user

    update = MagicMock()
    update.callback_query = query

    await trivia_callback(update, MagicMock())

    query.answer.assert_called_once_with("This isn't your question!", show_alert=True)


@pytest.mark.asyncio
async def test_trivia_callback_no_active_trivia():
    query = _make_trivia_query(user_id=1)
    update = MagicMock()
    update.callback_query = query

    ctx = MagicMock()
    ctx.user_data = {}  # no trivia stored

    await trivia_callback(update, ctx)

    query.answer.assert_called_with("No active trivia — use /trivia to play!")


@pytest.mark.asyncio
async def test_trivia_callback_correct_answer_gives_coins():
    query = _make_trivia_query(user_id=1, option="B")
    update = MagicMock()
    update.callback_query = query

    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=MagicMock())
    cm.__exit__ = MagicMock(return_value=False)

    ctx = MagicMock()
    ctx.user_data = {
        "trivia": {
            "answer": "B",
            "at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(),
            "answered": False,
        }
    }

    with patch("handlers.trivia.db.get_conn", return_value=cm):
        await trivia_callback(update, ctx)

    query.answer.assert_called_once()
    assert str(COINS_CORRECT) in str(query.answer.call_args)
    assert ctx.user_data["trivia"]["answered"] is True


@pytest.mark.asyncio
async def test_trivia_callback_wrong_answer_gives_consolation_coins():
    query = _make_trivia_query(user_id=1, option="A")  # wrong answer (correct is B)
    update = MagicMock()
    update.callback_query = query

    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=MagicMock())
    cm.__exit__ = MagicMock(return_value=False)

    ctx = MagicMock()
    ctx.user_data = {
        "trivia": {
            "answer": "B",
            "at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(),
            "answered": False,
        }
    }

    with patch("handlers.trivia.db.get_conn", return_value=cm):
        await trivia_callback(update, ctx)

    query.answer.assert_called_once()
    assert str(COINS_WRONG) in str(query.answer.call_args)


@pytest.mark.asyncio
async def test_trivia_callback_rejects_double_answer():
    query = _make_trivia_query(user_id=1, option="B")
    update = MagicMock()
    update.callback_query = query

    ctx = MagicMock()
    ctx.user_data = {
        "trivia": {
            "answer": "B",
            "at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(),
            "answered": True,  # already answered
        }
    }

    await trivia_callback(update, ctx)

    query.answer.assert_called_with("Already answered!")


@pytest.mark.asyncio
async def test_trivia_callback_window_expired():
    old_time = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=15)
    ).isoformat()

    query = _make_trivia_query(user_id=1, option="B")
    update = MagicMock()
    update.callback_query = query

    ctx = MagicMock()
    ctx.user_data = {
        "trivia": {
            "answer": "B",
            "at": old_time,
            "answered": False,
        }
    }

    await trivia_callback(update, ctx)

    query.answer.assert_called_with("Too slow!")
    assert ctx.user_data.get("trivia") is None
