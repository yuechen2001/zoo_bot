import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.admin import admin_command


def _make_update(user_id, args):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args
    return update, ctx


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, inner


# ── auth ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_rejects_non_admin():
    update, ctx = _make_update(user_id=9999, args=["coins", "100"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    update.message.reply_text.assert_called_once_with("⛔ Not authorised.")


# ── givecoin ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_givecoin_no_args_shows_usage():
    update, ctx = _make_update(user_id=1, args=["givecoin"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply


@pytest.mark.asyncio
async def test_givecoin_missing_amount_shows_usage():
    update, ctx = _make_update(user_id=1, args=["givecoin", "alice"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply


@pytest.mark.asyncio
async def test_givecoin_unknown_user_shows_error():
    update, ctx = _make_update(user_id=1, args=["givecoin", "nobody", "50"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=None
    ):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "not found" in reply.lower()


@pytest.mark.asyncio
async def test_givecoin_gives_coins_to_target():
    target = {"user_id": 42, "username": "alice", "coins": 100}
    updated = {"user_id": 42, "username": "alice", "coins": 150}
    cm, _ = _make_conn_mock()

    update, ctx = _make_update(user_id=1, args=["givecoin", "alice", "50"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ), patch("handlers.admin.db.get_user", return_value=updated), patch(
        "handlers.admin.db.get_conn", return_value=cm
    ):
        await admin_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "+50" in reply
    assert "alice" in reply
    assert "150" in reply


@pytest.mark.asyncio
async def test_givecoin_strips_at_symbol():
    """@alice and alice should resolve the same username."""
    target = {"user_id": 42, "username": "alice", "coins": 100}
    updated = {"user_id": 42, "username": "alice", "coins": 200}
    cm, _ = _make_conn_mock()

    update, ctx = _make_update(user_id=1, args=["givecoin", "@alice", "100"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ) as mock_lookup, patch("handlers.admin.db.get_user", return_value=updated), patch(
        "handlers.admin.db.get_conn", return_value=cm
    ):
        await admin_command(update, ctx)

    mock_lookup.assert_called_once_with("alice")  # @ stripped


@pytest.mark.asyncio
async def test_givecoin_negative_amount_deducts():
    """Admin can also take coins by passing a negative amount."""
    target = {"user_id": 42, "username": "alice", "coins": 100}
    updated = {"user_id": 42, "username": "alice", "coins": 50}
    cm, _ = _make_conn_mock()

    update, ctx = _make_update(user_id=1, args=["givecoin", "alice", "-50"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ), patch("handlers.admin.db.get_user", return_value=updated), patch(
        "handlers.admin.db.get_conn", return_value=cm
    ):
        await admin_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "-50" in reply


# ── giveuser ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_giveuser_no_args_shows_usage():
    update, ctx = _make_update(user_id=1, args=["giveuser"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_giveuser_unknown_user_shows_error():
    update, ctx = _make_update(user_id=1, args=["giveuser", "nobody", "Mouse"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=None
    ):
        await admin_command(update, ctx)
    assert "not found" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_giveuser_unknown_species_shows_error():
    target = {"user_id": 42, "username": "alice"}
    cm, inner = _make_conn_mock()
    inner.execute.return_value.fetchone.return_value = None
    inner.execute.return_value.fetchall.return_value = []

    update, ctx = _make_update(user_id=1, args=["giveuser", "alice", "Dragonfake"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ), patch("handlers.admin.db.get_conn", return_value=cm):
        await admin_command(update, ctx)
    assert "not found" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_giveuser_adds_animal_to_target():
    target = {"user_id": 42, "username": "alice"}
    species = MagicMock()
    species.__getitem__ = MagicMock(
        side_effect=lambda k: {"species_id": 5, "name": "Mouse", "emoji": "🐭"}[k]
    )
    cm, inner = _make_conn_mock()
    inner.execute.return_value.fetchone.return_value = species

    update, ctx = _make_update(user_id=1, args=["giveuser", "alice", "Mouse"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ), patch("handlers.admin.db.get_conn", return_value=cm), patch(
        "handlers.admin.db.add_animal"
    ) as mock_add:
        await admin_command(update, ctx)

    mock_add.assert_called_once()
    assert mock_add.call_args[0][1] == 42  # correct user_id
    assert "alice" in update.message.reply_text.call_args[0][0]


# ── listanimals ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_listanimals_no_args_shows_usage():
    update, ctx = _make_update(user_id=1, args=["listanimals"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_listanimals_unknown_user_shows_error():
    update, ctx = _make_update(user_id=1, args=["listanimals", "nobody"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=None
    ):
        await admin_command(update, ctx)
    assert "not found" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_listanimals_empty_zoo():
    target = {"user_id": 42, "username": "alice"}
    update, ctx = _make_update(user_id=1, args=["listanimals", "alice"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ), patch("handlers.admin.db.get_animals", return_value=[]):
        await admin_command(update, ctx)
    assert "no animals" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_listanimals_shows_animal_list():
    target = {"user_id": 42, "username": "alice"}
    animal = {
        "animal_id": "a1",
        "nickname": "Squeaky",
        "species_name": "Mouse",
        "emoji": "🐭",
        "hunger": 75,
        "rarity": "common",
        "is_breeding": 0,
    }
    update, ctx = _make_update(user_id=1, args=["listanimals", "alice"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ), patch("handlers.admin.db.get_animals", return_value=[animal]):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Squeaky" in reply
    assert "75" in reply
    assert "alice" in reply


# ── resetuser ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resetuser_no_args_shows_usage():
    update, ctx = _make_update(user_id=1, args=["resetuser"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_resetuser_unknown_user_shows_error():
    update, ctx = _make_update(user_id=1, args=["resetuser", "nobody"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=None
    ):
        await admin_command(update, ctx)
    assert "not found" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_resetuser_wipes_target_data():
    target = {"user_id": 42, "username": "alice"}
    cm, inner = _make_conn_mock()
    inner.execute.return_value.fetchall.return_value = []  # no animals

    update, ctx = _make_update(user_id=1, args=["resetuser", "alice"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ), patch("handlers.admin.db.get_conn", return_value=cm):
        await admin_command(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "alice" in reply
    assert "reset" in reply.lower()


# ── no args / unknown subcommand ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_no_args_shows_help():
    update, ctx = _make_update(user_id=1, args=[])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Admin Commands" in reply or "admin" in reply.lower()


@pytest.mark.asyncio
async def test_admin_unknown_subcommand_shows_error():
    update, ctx = _make_update(user_id=1, args=["boguscmd"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "unknown" in reply.lower() or "boguscmd" in reply


# ── coins ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_coins_no_args_shows_usage():
    update, ctx = _make_update(user_id=1, args=["coins"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_coins_adjusts_balance():
    user = {"user_id": 1, "coins": 600}
    cm, _ = _make_conn_mock()
    update, ctx = _make_update(user_id=1, args=["coins", "100"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user", return_value=user
    ), patch("handlers.admin.db.get_conn", return_value=cm):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "+100" in reply
    assert "600" in reply


@pytest.mark.asyncio
async def test_coins_negative_amount():
    user = {"user_id": 1, "coins": 400}
    cm, _ = _make_conn_mock()
    update, ctx = _make_update(user_id=1, args=["coins", "-100"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user", return_value=user
    ), patch("handlers.admin.db.get_conn", return_value=cm):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "-100" in reply


# ── reducecoin ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reducecoin_no_args_shows_usage():
    update, ctx = _make_update(user_id=1, args=["reducecoin"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_reducecoin_unknown_user_shows_error():
    update, ctx = _make_update(user_id=1, args=["reducecoin", "nobody", "50"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=None
    ):
        await admin_command(update, ctx)
    assert "not found" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_reducecoin_deducts_coins():
    target = {"user_id": 42, "username": "alice", "coins": 100}
    updated = {"user_id": 42, "username": "alice", "coins": 50}
    cm, _ = _make_conn_mock()
    update, ctx = _make_update(user_id=1, args=["reducecoin", "alice", "50"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user_by_username", return_value=target
    ), patch("handlers.admin.db.get_user", return_value=updated), patch(
        "handlers.admin.db.get_conn", return_value=cm
    ):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "50" in reply
    assert "alice" in reply


# ── hunger (set_stat) ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hunger_no_args_shows_usage():
    update, ctx = _make_update(user_id=1, args=["hunger"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_hunger_animal_not_found():
    update, ctx = _make_update(user_id=1, args=["hunger", "5", "80"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_animal_by_position", return_value=None
    ):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "no animal" in reply.lower() or "position" in reply.lower()


@pytest.mark.asyncio
async def test_hunger_sets_stat():
    animal = {
        "animal_id": "a1",
        "nickname": "Buddy",
        "species_name": "Mouse",
        "emoji": "🐭",
    }
    update, ctx = _make_update(user_id=1, args=["hunger", "1", "80"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_animal_by_position", return_value=animal
    ), patch("handlers.admin.db.admin_set_animal_stat") as mock_set:
        await admin_command(update, ctx)
    mock_set.assert_called_once_with("a1", "hunger", 80)
    reply = update.message.reply_text.call_args[0][0]
    assert "Buddy" in reply


# ── pause / resume ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pause_no_args_shows_usage():
    update, ctx = _make_update(user_id=1, args=["pause"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    assert (
        "Usage" in update.message.reply_text.call_args[0][0]
        or "pause" in update.message.reply_text.call_args[0][0].lower()
    )


@pytest.mark.asyncio
async def test_pause_invalid_format():
    update, ctx = _make_update(user_id=1, args=["pause", "badformat"])
    with patch("handlers.admin.ADMIN_IDS", {1}):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "format" in reply.lower() or "pause" in reply.lower()


@pytest.mark.asyncio
async def test_pause_hours_without_group():
    user = {"user_id": 1, "group_chat_id": None}
    update, ctx = _make_update(user_id=1, args=["pause", "2h"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user", return_value=user
    ), patch("handlers.admin.db.set_paused_until") as mock_pause:
        await admin_command(update, ctx)
    mock_pause.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "paused" in reply.lower()


@pytest.mark.asyncio
async def test_pause_minutes_with_group():
    user = {"user_id": 1, "group_chat_id": -100}
    update, ctx = _make_update(user_id=1, args=["pause", "30m"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user", return_value=user
    ), patch("handlers.admin.db.set_group_paused_until") as mock_pause:
        await admin_command(update, ctx)
    mock_pause.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "paused" in reply.lower()


@pytest.mark.asyncio
async def test_resume_without_group():
    user = {"user_id": 1, "group_chat_id": None}
    update, ctx = _make_update(user_id=1, args=["resume"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user", return_value=user
    ), patch("handlers.admin.db.set_paused_until") as mock_resume:
        await admin_command(update, ctx)
    mock_resume.assert_called_once_with(1, None)
    reply = update.message.reply_text.call_args[0][0]
    assert "resumed" in reply.lower()


@pytest.mark.asyncio
async def test_resume_with_group():
    user = {"user_id": 1, "group_chat_id": -100}
    update, ctx = _make_update(user_id=1, args=["resume"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_user", return_value=user
    ), patch("handlers.admin.db.set_group_paused_until") as mock_resume:
        await admin_command(update, ctx)
    mock_resume.assert_called_once_with(-100, None)


# ── reset ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_wipes_own_data():
    update, ctx = _make_update(user_id=1, args=["reset"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.reset_user_data"
    ) as mock_reset:
        await admin_command(update, ctx)
    mock_reset.assert_called_once_with(1)
    reply = update.message.reply_text.call_args[0][0]
    assert "reset" in reply.lower()


# ── stats ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stats_shows_db_summary():
    stats = {
        "users": 5,
        "animals": 12,
        "breeding": 2,
        "checkins": 99,
        "by_rarity": [{"rarity": "common", "n": 8}, {"rarity": "rare", "n": 4}],
    }
    update, ctx = _make_update(user_id=1, args=["stats"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.get_bot_stats", return_value=stats
    ):
        await admin_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "5" in reply
    assert "12" in reply
    assert "common" in reply


# ── tick ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tick_fires_scheduler():
    update, ctx = _make_update(user_id=1, args=["tick"])
    tick_mock = AsyncMock()
    mock_sched = MagicMock()
    mock_sched.tick = tick_mock
    with patch("handlers.admin.ADMIN_IDS", {1}), patch.dict(
        "sys.modules", {"scheduler": mock_sched}
    ):
        await admin_command(update, ctx)
    tick_mock.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "tick" in reply.lower() or "✅" in reply


# ── prompt ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prompt_sends_mood_message():
    update, ctx = _make_update(user_id=1, args=["prompt"])
    with patch("handlers.admin.ADMIN_IDS", {1}), patch(
        "handlers.admin.db.set_last_prompt_at"
    ) as mock_set:
        await admin_command(update, ctx)
    mock_set.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "mood" in reply.lower() or "check-in" in reply.lower()
