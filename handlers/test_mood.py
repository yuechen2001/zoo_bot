import datetime
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.mood import (
    mood_checkin_callback,
    pause_command,
    resume_command,
    moodstart_command,
    moodstop_command,
    help_command,
    help_tab_callback,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


@pytest.fixture(autouse=True)
def no_achievements(monkeypatch):
    monkeypatch.setattr("game.achievements.check_achievements", AsyncMock())


def _make_cmd_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_user_row(**kw):
    defaults = {
        "user_id": 1,
        "opted_in": 0,
        "streak_windows": 5,
        "consecutive_misses": 1,
        "mood_booster_active": 0,
    }
    return make_row(**{**defaults, **kw})


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


# ── /moodstart and /moodstop ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_moodstart_rejects_unknown_user():
    update = _make_cmd_update()
    with patch("handlers.mood.db.get_user", return_value=None):
        await moodstart_command(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_moodstart_sets_opted_in():
    update = _make_cmd_update()
    conn_mock = MagicMock()
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn_mock)
    conn_ctx.__exit__ = MagicMock(return_value=False)

    with patch("handlers.mood.db.get_user", return_value=_make_user_row()), patch(
        "handlers.mood.db.get_conn", return_value=conn_ctx
    ):
        await moodstart_command(update, MagicMock())

    conn_mock.execute.assert_called_once()
    sql = conn_mock.execute.call_args[0][0]
    assert "opted_in = 1" in sql
    reply = update.message.reply_text.call_args[0][0]
    assert "enabled" in reply.lower()


@pytest.mark.asyncio
async def test_moodstop_preserves_streak():
    update = _make_cmd_update()
    conn_mock = MagicMock()
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn_mock)
    conn_ctx.__exit__ = MagicMock(return_value=False)

    with patch("handlers.mood.db.get_user", return_value=_make_user_row(streak_windows=10)), patch(
        "handlers.mood.db.get_conn", return_value=conn_ctx
    ):
        await moodstop_command(update, MagicMock())

    sql = conn_mock.execute.call_args[0][0]
    assert "streak_windows" not in sql, "moodstop must not reset streak_windows"
    assert "opted_in = 0" in sql
    reply = update.message.reply_text.call_args[0][0]
    assert "preserved" in reply.lower()


# ── Mood prompt shared group check-in ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_mood_callback_rejects_unregistered_user():
    query = _make_query(user_id=456)
    update = _make_update(query)

    with patch("handlers.mood.db.get_user", return_value=None):
        await mood_checkin_callback(update, MagicMock())

    query.answer.assert_called_once_with("Use /start first!", show_alert=True)


@pytest.mark.asyncio
async def test_mood_callback_rejects_non_opted_in_user():
    query = _make_query(user_id=456)
    update = _make_update(query)

    user_data = {
        "opted_in": 0,
        "last_prompt_at": None,
        "last_checkin_at": None,
        "streak_windows": 0,
    }
    with patch("handlers.mood.db.get_user", return_value=user_data):
        await mood_checkin_callback(update, MagicMock())

    query.answer.assert_called_once_with(
        "Use /moodstart to opt in to prompts first!", show_alert=True
    )


@pytest.mark.asyncio
async def test_mood_callback_window_closed():
    old_prompt = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=20)
    ).isoformat()
    user_data = {
        "opted_in": 1,
        "last_prompt_at": old_prompt,
        "last_checkin_at": None,
        "streak_windows": 0,
        "group_chat_id": None,
    }

    query = _make_query(user_id=123)
    update = _make_update(query)

    with patch("handlers.mood.db.get_user", return_value=user_data):
        await mood_checkin_callback(update, MagicMock())

    # Window-closed now uses show_alert popup, NOT edit_message_text
    query.answer.assert_called_once()
    args, kwargs = query.answer.call_args
    assert kwargs.get("show_alert") is True
    assert "closed" in args[0].lower()
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_mood_callback_second_player_can_respond():
    """After player A responds, player B's click should still earn coins (not be blocked)."""
    prompt_time = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=2)
    ).isoformat()

    def _user(user_id, checked_in=False):
        return {
            "user_id": user_id,
            "opted_in": 1,
            "last_prompt_at": prompt_time,
            "last_checkin_at": (
                (
                    datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    - datetime.timedelta(minutes=1)
                ).isoformat()
                if checked_in
                else None
            ),
            "streak_windows": 0,
            "group_chat_id": -100,
            "mood_booster_active": 0,
        }

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=MagicMock())
    mock_conn.__exit__ = MagicMock(return_value=False)

    # Player B has not yet checked in
    query = _make_query(user_id=2)
    update = _make_update(query)

    with patch("handlers.mood.db.get_user", return_value=_user(2, checked_in=False)), patch(
        "handlers.mood.db.get_conn", return_value=mock_conn
    ), patch("handlers.mood.db.record_prompt_response", return_value=True), patch(
        "handlers.mood.db.all_group_members_checked_in", return_value=False
    ), patch(
        "game.achievements.check_achievements"
    ):
        await mood_checkin_callback(update, MagicMock())

    # Player B should receive a coins popup
    query.answer.assert_called_once()
    args, kwargs = query.answer.call_args
    assert "coins" in args[0].lower()
    assert kwargs.get("show_alert") is True
    # Group message must NOT be edited (keyboard preserved for others)
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_mood_callback_collapses_when_all_checked_in():
    """When everyone in the group has responded, the message should be edited to summary."""
    prompt_time = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=2)
    ).isoformat()
    user_data = {
        "opted_in": 1,
        "last_prompt_at": prompt_time,
        "last_checkin_at": None,
        "streak_windows": 0,
        "group_chat_id": -100,
        "mood_booster_active": 0,
    }

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=MagicMock())
    mock_conn.__exit__ = MagicMock(return_value=False)

    query = _make_query(user_id=1)
    update = _make_update(query)

    with patch("handlers.mood.db.get_user", return_value=user_data), patch(
        "handlers.mood.db.get_conn", return_value=mock_conn
    ), patch("handlers.mood.db.record_prompt_response", return_value=True), patch(
        "handlers.mood.db.all_group_members_checked_in", return_value=True
    ), patch(
        "game.achievements.check_achievements"
    ):
        await mood_checkin_callback(update, MagicMock())

    # Message should be collapsed to summary
    query.edit_message_text.assert_called_once()
    args = query.edit_message_text.call_args[0]
    assert "everyone" in args[0].lower() or "✅" in args[0]


@pytest.mark.asyncio
async def test_mood_callback_rejects_double_tap():
    prompt_time = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=2)
    ).isoformat()
    user_data = {
        "opted_in": 1,
        "last_prompt_at": prompt_time,
        "last_checkin_at": None,
        "streak_windows": 0,
        "group_chat_id": None,
    }

    query = _make_query(user_id=123)
    update = _make_update(query)

    # record_prompt_response returns False → user already responded
    with patch("handlers.mood.db.get_user", return_value=user_data), patch(
        "handlers.mood.db.record_prompt_response", return_value=False
    ):
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


@pytest.mark.asyncio
async def test_help_footmassage_in_zoo_section():
    from handlers.mood import _HELP_SECTIONS

    # /footmassage is in the zoo tab
    assert "/footmassage" in _HELP_SECTIONS["zoo"]
    # /footmassage is not in the mood/more tab
    assert "/footmassage" not in _HELP_SECTIONS["more"]
    # help_command sends the zoo tab first
    update = _make_cmd_update()
    await help_command(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "/footmassage" in text


# ── moodstop unknown user ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_moodstop_rejects_unknown_user():
    update = _make_cmd_update()
    with patch("handlers.mood.db.get_user", return_value=None):
        await moodstop_command(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Use /start first!")


# ── pause edge cases ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pause_rejects_unknown_user():
    update = _make_cmd_update(user_id=1)
    with patch("handlers.mood.ADMIN_IDS", {1}), patch(
        "handlers.mood.db.get_user", return_value=None
    ):
        await pause_command(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_pause_rejects_no_args():
    update = _make_cmd_update(user_id=1)
    ctx = MagicMock()
    ctx.args = []
    with patch("handlers.mood.ADMIN_IDS", {1}), patch(
        "handlers.mood.db.get_user", return_value={"streak_windows": 0}
    ):
        await pause_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply


@pytest.mark.asyncio
async def test_pause_rejects_invalid_format():
    update = _make_cmd_update(user_id=1)
    ctx = MagicMock()
    ctx.args = ["2days"]
    with patch("handlers.mood.ADMIN_IDS", {1}), patch(
        "handlers.mood.db.get_user", return_value={"streak_windows": 0}
    ):
        await pause_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Format" in reply


# ── checkin branch coverage ────────────────────────────────────────────────────


def _checkin_user(**kw):
    base = {
        "user_id": 1,
        "opted_in": 1,
        "streak_windows": 1,
        "group_chat_id": None,
        "last_prompt_at": (
            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            - datetime.timedelta(minutes=2)
        ).isoformat(),
        "mood_booster_active": 0,
    }
    return {**base, **kw}


@pytest.mark.asyncio
async def test_mood_callback_no_last_prompt_still_succeeds():
    user = _checkin_user(last_prompt_at=None)
    query = _make_query(user_id=1)
    update = _make_update(query)
    with patch("handlers.mood.db.get_user", return_value=user), patch(
        "handlers.mood.db.record_prompt_response", return_value=True
    ), patch("handlers.mood.db.record_checkin"), patch("game.achievements.check_achievements"):
        await mood_checkin_callback(update, MagicMock())
    query.answer.assert_called_once()
    assert "coins" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_mood_callback_mood_booster_doubles_coins():
    user = _checkin_user(mood_booster_active=1)
    query = _make_query(user_id=1, emoji="🤩")
    update = _make_update(query)
    with patch("handlers.mood.db.get_user", return_value=user), patch(
        "handlers.mood.db.record_prompt_response", return_value=True
    ), patch("handlers.mood.db.record_checkin"), patch(
        "handlers.mood.db.set_mood_booster"
    ) as mock_clear, patch(
        "game.achievements.check_achievements"
    ):
        await mood_checkin_callback(update, MagicMock())
    mock_clear.assert_called_once_with(1, False)
    assert "coins" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_mood_callback_streak_multiplier_shown():
    user = _checkin_user(streak_windows=4)  # new_streak becomes 5 → shows multiplier
    query = _make_query(user_id=1)
    update = _make_update(query)
    with patch("handlers.mood.db.get_user", return_value=user), patch(
        "handlers.mood.db.record_prompt_response", return_value=True
    ), patch("handlers.mood.db.record_checkin"), patch("game.achievements.check_achievements"):
        await mood_checkin_callback(update, MagicMock())
    reply = query.answer.call_args[0][0]
    assert "streak bonus" in reply.lower()


@pytest.mark.asyncio
async def test_mood_callback_group_chat_id_synced():
    user = _checkin_user(group_chat_id=None)
    query = _make_query(user_id=1)
    query.message.chat.type = "supergroup"
    query.message.chat_id = -500
    update = _make_update(query)
    with patch("handlers.mood.db.get_user", return_value=user), patch(
        "handlers.mood.db.update_group_chat_id"
    ) as mock_sync, patch("handlers.mood.db.record_prompt_response", return_value=True), patch(
        "handlers.mood.db.record_checkin"
    ), patch(
        "game.achievements.check_achievements"
    ):
        await mood_checkin_callback(update, MagicMock())
    mock_sync.assert_called_once_with(1, -500)


@pytest.mark.asyncio
async def test_mood_callback_group_collapse_exception_swallowed():
    prompt_time = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=2)
    ).isoformat()
    user = _checkin_user(group_chat_id=-100, last_prompt_at=prompt_time)
    query = _make_query(user_id=1)
    query.edit_message_text = AsyncMock(side_effect=Exception("flood"))
    update = _make_update(query)
    with patch("handlers.mood.db.get_user", return_value=user), patch(
        "handlers.mood.db.record_prompt_response", return_value=True
    ), patch("handlers.mood.db.record_checkin"), patch(
        "handlers.mood.db.all_group_members_checked_in", return_value=True
    ), patch(
        "game.achievements.check_achievements"
    ):
        await mood_checkin_callback(update, MagicMock())  # must not raise
    query.answer.assert_called_once()


# ── help_tab_callback ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_help_tab_callback_renders_requested_section():
    query = MagicMock()
    query.data = "help_tab_breeding"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query

    await help_tab_callback(update, MagicMock())

    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args[0][0]
    assert "Breeding" in text or "/breed" in text


@pytest.mark.asyncio
async def test_help_tab_callback_unknown_section_falls_back_to_zoo():
    query = MagicMock()
    query.data = "help_tab_nonexistent"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query

    await help_tab_callback(update, MagicMock())

    text = query.edit_message_text.call_args[0][0]
    assert "/zoo" in text
