import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import db
from scheduler import (
    _check_starved_animals,
    _decay_stats,
    _check_hunger_alerts,
    _cleanup_expired_trades,
    _check_breed_completions,
    wild_event_tick,
    _send_mood_prompts,
    _cleanup_expired_prompts,
    cleanup_expired_wild_events,
)
from conftest import make_row


def _ago(minutes: float) -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=minutes)
    ).isoformat()


def _mock_user(
    tg_id=1, group_chat_id=-100, last_prompt=None, consecutive_misses=0, username="alice"
):
    return make_row(
        user_id=tg_id,
        group_chat_id=group_chat_id,
        last_prompt_at=last_prompt,
        consecutive_misses=consecutive_misses,
        username=username,
    )


def _group_state(last_prompt_at):
    return make_row(group_chat_id=-100, last_prompt_at=last_prompt_at)


@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch("db.DATABASE_PATH", db_path):
        db.init_db()
        yield db_path


def _insert_user_and_animal(db_path, animal_id, hunger, is_breeding=0, group_chat_id=-100):
    with patch("db.DATABASE_PATH", db_path):
        db.ensure_user(1, "tester", group_chat_id)
        species_id = db.get_all_species()[0]["species_id"]
        db.add_animal(
            animal_id, 1, species_id, nickname="Buddy", hunger=hunger, is_breeding=is_breeding
        )


# ── starvation ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_starved_animal_deleted(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=0)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_starved_animals(ctx)
        row = db.get_animal("a1")

    assert row is None


@pytest.mark.asyncio
async def test_starved_animal_notification_sent(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=0, group_chat_id=-100)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_starved_animals(ctx)

    ctx.bot.send_message.assert_called_once()
    call_kwargs = ctx.bot.send_message.call_args
    assert call_kwargs[0][0] == -100  # sent to group chat


@pytest.mark.asyncio
async def test_hungry_but_not_zero_not_deleted(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=1)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_starved_animals(ctx)
        row = db.get_animal("a1")

    assert row is not None


@pytest.mark.asyncio
async def test_breeding_animal_not_deleted_when_hunger_zero(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=0, is_breeding=1)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_starved_animals(ctx)
        row = db.get_animal("a1")

    assert row is not None  # breeding animals are exempt from starvation


# ── hunger decay ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decay_reduces_hunger(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=100)

    with patch("db.DATABASE_PATH", temp_db):
        await _decay_stats()
        animal = db.get_animal("a1")
        # Hunger should have dropped by hunger_decay (varies by species, >= 1)
        assert animal["hunger"] < 100


@pytest.mark.asyncio
async def test_decay_does_not_go_below_zero(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=0)

    with patch("db.DATABASE_PATH", temp_db):
        await _decay_stats()
        animal = db.get_animal("a1")

    assert animal["hunger"] == 0


@pytest.mark.asyncio
async def test_breeding_animals_not_decayed(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=80, is_breeding=1)

    with patch("db.DATABASE_PATH", temp_db):
        await _decay_stats()
        animal = db.get_animal("a1")

    assert animal["hunger"] == 80  # breeding animals skip decay


# ── hunger alerts ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hunger_alert_at_20(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=15)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_hunger_alerts(ctx)

    ctx.bot.send_message.assert_called_once()
    msg = ctx.bot.send_message.call_args[0][1]
    assert "hungry" in msg.lower() or "⚠️" in msg


@pytest.mark.asyncio
async def test_hunger_alert_at_10(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=8)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_hunger_alerts(ctx)
        db.set_hunger_alerted("a1", 20)

    # Second call should escalate to threshold-10 alert
    ctx.bot.send_message.reset_mock()
    with patch("db.DATABASE_PATH", temp_db):
        await _check_hunger_alerts(ctx)

    ctx.bot.send_message.assert_called()


@pytest.mark.asyncio
async def test_hunger_alert_not_repeated_for_same_threshold(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=15)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_hunger_alerts(ctx)
        # Second tick — alerted=20 is already set
        ctx.bot.send_message.reset_mock()
        await _check_hunger_alerts(ctx)

    ctx.bot.send_message.assert_not_called()


# ── trade expiry ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expired_trade_notifies_proposer(temp_db):
    with patch("db.DATABASE_PATH", temp_db):
        db.ensure_user(1, "alice", -100)
        db.ensure_user(2, "bob", -100)
        species_id = db.get_all_species()[0]["species_id"]
        db.add_animal("a1", 1, species_id)
        db.add_animal("b1", 2, species_id)
        old_time = (
            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            - datetime.timedelta(minutes=30)
        ).isoformat()
        trade_id = db.create_trade(1, 2, "a1", "b1", created_at=old_time)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _cleanup_expired_trades(ctx)
        trade = db.get_trade(trade_id)
    assert trade["status"] == "expired"
    ctx.bot.send_message.assert_called_once()


# ── breed-ready notifications ─────────────────────────────────────────────────


def _insert_ready_breed(db_path, last_notified_at=None):
    """Insert a completed breed into the queue for notification tests."""
    with patch("db.DATABASE_PATH", db_path):
        db.ensure_user(1, "tester", -100)
        species_id = db.get_all_species()[0]["species_id"]
        db.add_animal("pa", 1, species_id, is_breeding=1)
        db.add_animal("pb", 1, species_id, is_breeding=1)
        past = (
            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            - datetime.timedelta(hours=2)
        ).isoformat()
        db.insert_breed_queue_entry(
            1, "pa", "pb", species_id, past, last_notified_at=last_notified_at
        )


@pytest.mark.asyncio
async def test_breed_ready_notifies_on_first_completion(temp_db):
    _insert_ready_breed(temp_db, last_notified_at=None)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_breed_completions(ctx)

    ctx.bot.send_message.assert_called_once()
    msg = ctx.bot.send_message.call_args[0][1]
    assert "Breeding complete" in msg or "breed" in msg.lower()


@pytest.mark.asyncio
async def test_breed_ready_marks_notified_after_send(temp_db):
    _insert_ready_breed(temp_db, last_notified_at=None)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_breed_completions(ctx)
        breed = db.get_pending_breed(1)
    assert breed["last_notified_at"] is not None


@pytest.mark.asyncio
async def test_breed_ready_no_repeat_within_interval(temp_db):
    """A breed notified 5 minutes ago should NOT trigger another notification (interval=30min)."""
    recent = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=5)
    ).isoformat()
    _insert_ready_breed(temp_db, last_notified_at=recent)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_breed_completions(ctx)

    ctx.bot.send_message.assert_not_called()


# ── wild event tick ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wild_event_tick_message_format():
    species = make_row(
        species_id=1,
        name="Mouse",
        emoji="🐭",
        rarity="common",
        habitat="woodland",
        catch_rate=0.90,
    )
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock(return_value=MagicMock(message_id=42))
    ctx.bot.edit_message_reply_markup = AsyncMock()
    ctx.job_queue.run_once = MagicMock()

    with patch("scheduler.db.get_active_group_chats", return_value=[-100]), patch(
        "scheduler.db.get_species_candidates", return_value=[species]
    ), patch("scheduler.db.create_wild_event", return_value=1), patch(
        "scheduler.db.set_setting"
    ), patch(
        "scheduler.random.randint", return_value=60
    ):
        await wild_event_tick(ctx)

    text = ctx.bot.send_message.call_args[0][1]
    assert "Common ⬜ | 🌲 Woodland" in text
    assert "Catch rate: 90%" in text
    assert "5 min" in text


@pytest.mark.asyncio
async def test_breed_ready_reminds_after_interval(temp_db):
    """A breed notified 35 minutes ago SHOULD trigger a reminder (interval=30min)."""
    old = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(minutes=35)
    ).isoformat()
    _insert_ready_breed(temp_db, last_notified_at=old)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_breed_completions(ctx)

    ctx.bot.send_message.assert_called_once()
    msg = ctx.bot.send_message.call_args[0][1]
    assert "reminder" in msg.lower() or "ready" in msg.lower()


# ── _send_mood_prompts ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_mood_prompts_no_users():
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    with patch("scheduler.db.get_all_active_users", return_value=[]):
        await _send_mood_prompts(ctx)
    ctx.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_mood_prompts_responded_user_no_miss():
    user = _mock_user(last_prompt=_ago(35))
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    ctx.bot_data = {}
    with patch("scheduler.db.get_all_active_users", return_value=[user]), patch(
        "scheduler.db.has_prompt_response", return_value=True
    ), patch("scheduler.db.get_group_state", return_value=_group_state(_ago(35))), patch(
        "scheduler.db.set_group_last_prompt"
    ), patch(
        "scheduler.db.bulk_set_last_prompt_at"
    ), patch(
        "scheduler.db.set_consecutive_misses"
    ) as mock_miss:
        await _send_mood_prompts(ctx)
    mock_miss.assert_not_called()


@pytest.mark.asyncio
async def test_send_mood_prompts_missed_once_increments():
    user = _mock_user(last_prompt=_ago(35), consecutive_misses=0)
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    ctx.bot_data = {}
    with patch("scheduler.db.get_all_active_users", return_value=[user]), patch(
        "scheduler.db.has_prompt_response", return_value=False
    ), patch("scheduler.db.get_group_state", return_value=_group_state(_ago(35))), patch(
        "scheduler.db.set_group_last_prompt"
    ), patch(
        "scheduler.db.bulk_set_last_prompt_at"
    ), patch(
        "scheduler.db.set_consecutive_misses"
    ) as mock_miss:
        await _send_mood_prompts(ctx)
    mock_miss.assert_called_once_with(1, 1)


@pytest.mark.asyncio
async def test_send_mood_prompts_missed_twice_resets_streak():
    user = _mock_user(last_prompt=_ago(35), consecutive_misses=1, username="alice")
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    ctx.bot_data = {}
    with patch("scheduler.db.get_all_active_users", return_value=[user]), patch(
        "scheduler.db.has_prompt_response", return_value=False
    ), patch("scheduler.db.get_group_state", return_value=_group_state(_ago(35))), patch(
        "scheduler.db.reset_user_streak"
    ) as mock_reset, patch(
        "scheduler.db.set_group_last_prompt"
    ), patch(
        "scheduler.db.bulk_set_last_prompt_at"
    ):
        await _send_mood_prompts(ctx)
    mock_reset.assert_called_once_with(1)
    texts = [c[0][1] for c in ctx.bot.send_message.call_args_list]
    assert any("💔" in t or "streak" in t.lower() for t in texts)


@pytest.mark.asyncio
async def test_send_mood_prompts_both_missed_plural_message():
    user1 = _mock_user(tg_id=1, last_prompt=_ago(35), consecutive_misses=1, username="alice")
    user2 = _mock_user(tg_id=2, last_prompt=_ago(35), consecutive_misses=1, username="bob")
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    ctx.bot_data = {}
    with patch("scheduler.db.get_all_active_users", return_value=[user1, user2]), patch(
        "scheduler.db.has_prompt_response", return_value=False
    ), patch("scheduler.db.get_group_state", return_value=_group_state(_ago(35))), patch(
        "scheduler.db.reset_user_streak"
    ), patch(
        "scheduler.db.set_group_last_prompt"
    ), patch(
        "scheduler.db.bulk_set_last_prompt_at"
    ):
        await _send_mood_prompts(ctx)
    texts = [c[0][1] for c in ctx.bot.send_message.call_args_list]
    assert any("both" in t.lower() for t in texts)


@pytest.mark.asyncio
async def test_send_mood_prompts_skips_recent_group():
    user = _mock_user(last_prompt=_ago(35))
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    ctx.bot_data = {}
    with patch("scheduler.db.get_all_active_users", return_value=[user]), patch(
        "scheduler.db.has_prompt_response", return_value=True
    ), patch("scheduler.db.get_group_state", return_value=_group_state(_ago(0.1))), patch(
        "scheduler.PROMPT_INTERVAL_MINUTES", 30
    ), patch(
        "scheduler.db.set_group_last_prompt"
    ) as mock_set:
        await _send_mood_prompts(ctx)
    mock_set.assert_not_called()


@pytest.mark.asyncio
async def test_send_mood_prompts_sends_when_due():
    user = _mock_user(last_prompt=_ago(35))
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    ctx.bot_data = {}
    with patch("scheduler.db.get_all_active_users", return_value=[user]), patch(
        "scheduler.db.has_prompt_response", return_value=True
    ), patch("scheduler.db.get_group_state", return_value=_group_state(_ago(35))), patch(
        "scheduler.db.set_group_last_prompt"
    ) as mock_set, patch(
        "scheduler.db.bulk_set_last_prompt_at"
    ):
        await _send_mood_prompts(ctx)
    mock_set.assert_called_once()
    text = ctx.bot.send_message.call_args[0][1]
    assert "Mood check-in" in text


@pytest.mark.asyncio
async def test_send_mood_prompts_sends_when_no_group_state():
    user = _mock_user()
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    ctx.bot_data = {}
    with patch("scheduler.db.get_all_active_users", return_value=[user]), patch(
        "scheduler.db.has_prompt_response", return_value=True
    ), patch("scheduler.db.get_group_state", return_value=None), patch(
        "scheduler.db.set_group_last_prompt"
    ) as mock_set, patch(
        "scheduler.db.bulk_set_last_prompt_at"
    ):
        await _send_mood_prompts(ctx)
    mock_set.assert_called_once()


# ── cleanup_expired_wild_events ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cleanup_expired_wild_events_edits_and_claims():
    event = make_row(id=1, group_chat_id=-100, message_id=42)
    ctx = MagicMock()
    ctx.bot.edit_message_text = AsyncMock()
    with patch("scheduler.db.get_expired_wild_events", return_value=[event]), patch(
        "scheduler.db.claim_wild_event"
    ) as mock_claim:
        await cleanup_expired_wild_events(ctx)
    ctx.bot.edit_message_text.assert_called_once()
    assert "got away" in ctx.bot.edit_message_text.call_args[1]["text"].lower()
    mock_claim.assert_called_once_with(1, -1)


@pytest.mark.asyncio
async def test_cleanup_expired_wild_events_no_events():
    ctx = MagicMock()
    ctx.bot.edit_message_text = AsyncMock()
    with patch("scheduler.db.get_expired_wild_events", return_value=[]):
        await cleanup_expired_wild_events(ctx)
    ctx.bot.edit_message_text.assert_not_called()


# ── _cleanup_expired_prompts ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cleanup_expired_prompts_removes_expired():
    expired_at = _ago(20)
    ctx = MagicMock()
    ctx.bot_data = {"prompt_messages": {-100: {"message_id": 42, "sent_at": expired_at}}}
    ctx.bot.edit_message_reply_markup = AsyncMock()
    await _cleanup_expired_prompts(ctx)
    ctx.bot.edit_message_reply_markup.assert_called_once_with(
        chat_id=-100, message_id=42, reply_markup=None
    )
    assert -100 not in ctx.bot_data["prompt_messages"]


@pytest.mark.asyncio
async def test_cleanup_expired_prompts_keeps_recent():
    recent = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    ctx = MagicMock()
    ctx.bot_data = {"prompt_messages": {-100: {"message_id": 42, "sent_at": recent}}}
    ctx.bot.edit_message_reply_markup = AsyncMock()
    await _cleanup_expired_prompts(ctx)
    ctx.bot.edit_message_reply_markup.assert_not_called()
    assert -100 in ctx.bot_data["prompt_messages"]
