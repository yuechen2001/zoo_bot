import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.mood import mood_checkin_callback, pause_command, resume_command


def _make_query(user_id: int, emoji: str = "🙂"):
    query = MagicMock()
    query.data = f"mood_{emoji}"
    query.from_user.id = user_id
    query.from_user.first_name = "TestUser"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


def _make_update(query):
    update = MagicMock()
    update.callback_query = query
    return update


# ── Mood prompt shared group check-in ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_mood_callback_rejects_unregistered_user():
    query = _make_query(user_id=456)
    update = _make_update(query)

    with patch("handlers.mood.db.get_user", return_value=None):
        await mood_checkin_callback(update, MagicMock())

    query.answer.assert_called_once_with("Use /start first to join!", show_alert=True)


@pytest.mark.asyncio
async def test_mood_callback_rejects_non_opted_in_user():
    query = _make_query(user_id=456)
    update = _make_update(query)

    user_data = {"opted_in": 0, "last_prompt_at": None, "last_checkin_at": None, "streak_windows": 0}
    with patch("handlers.mood.db.get_user", return_value=user_data):
        await mood_checkin_callback(update, MagicMock())

    query.answer.assert_called_once_with("Use /moodstart to opt in to prompts first!", show_alert=True)


@pytest.mark.asyncio
async def test_mood_callback_window_closed():
    old_prompt = (datetime.datetime.utcnow() - datetime.timedelta(minutes=20)).isoformat()
    user_data = {"opted_in": 1, "last_prompt_at": old_prompt, "last_checkin_at": None, "streak_windows": 0}

    query = _make_query(user_id=123)
    update = _make_update(query)

    with patch("handlers.mood.db.get_user", return_value=user_data):
        await mood_checkin_callback(update, MagicMock())

    query.answer.assert_called_with("Window closed!")


@pytest.mark.asyncio
async def test_mood_callback_rejects_double_tap():
    prompt_time = (datetime.datetime.utcnow() - datetime.timedelta(minutes=2)).isoformat()
    checkin_time = (datetime.datetime.utcnow() - datetime.timedelta(minutes=1)).isoformat()
    user_data = {
        "opted_in": 1,
        "last_prompt_at": prompt_time,
        "last_checkin_at": checkin_time,  # checkin AFTER prompt → already responded
        "streak_windows": 0,
    }

    query = _make_query(user_id=123)
    update = _make_update(query)

    with patch("handlers.mood.db.get_user", return_value=user_data):
        await mood_checkin_callback(update, MagicMock())

    query.answer.assert_called_with("Already checked in for this prompt!")


# ── Fix 2: admin-only pause/resume ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pause_rejects_non_admin():
    update = MagicMock()
    update.effective_user.id = 9999
    update.message.reply_text = AsyncMock()

    with patch("handlers.mood.ADMIN_IDS", {1, 2}):
        await pause_command(update, MagicMock())

    update.message.reply_text.assert_called_once_with("❌ Only admins can use /pause.")


@pytest.mark.asyncio
async def test_resume_rejects_non_admin():
    update = MagicMock()
    update.effective_user.id = 9999
    update.message.reply_text = AsyncMock()

    with patch("handlers.mood.ADMIN_IDS", {1, 2}):
        await resume_command(update, MagicMock())

    update.message.reply_text.assert_called_once_with("❌ Only admins can use /resume.")


@pytest.mark.asyncio
async def test_pause_accepted_for_admin():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.args = ["8h"]

    mock_inner = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_inner)
    mock_cm.__exit__ = MagicMock(return_value=False)

    with patch("handlers.mood.ADMIN_IDS", {1}), patch(
        "handlers.mood.db.get_user", return_value={"streak_windows": 0}
    ), patch("handlers.mood.db.get_conn", return_value=mock_cm):
        await pause_command(update, ctx)

    update.message.reply_text.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "⏸" in reply or "Paused" in reply


@pytest.mark.asyncio
async def test_resume_accepted_for_admin():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    mock_inner = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_inner)
    mock_cm.__exit__ = MagicMock(return_value=False)

    with patch("handlers.mood.ADMIN_IDS", {1}), patch(
        "handlers.mood.db.get_conn", return_value=mock_cm
    ):
        await resume_command(update, MagicMock())

    update.message.reply_text.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "▶️" in reply or "Resumed" in reply
