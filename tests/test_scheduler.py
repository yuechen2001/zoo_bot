import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import db
from scheduler import (
    _check_starved_animals,
    _decay_stats,
    _check_hunger_alerts,
    _cleanup_expired_trades,
)


@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch("db.DATABASE_PATH", db_path):
        db.init_db()
        yield db_path


def _insert_user_and_animal(db_path, animal_id, hunger, is_breeding=0, group_chat_id=-100):
    with patch("db.DATABASE_PATH", db_path):
        with db.get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, group_chat_id) VALUES (1, 'tester', ?)",
                (group_chat_id,),
            )
            species_id = conn.execute("SELECT species_id FROM species LIMIT 1").fetchone()[
                "species_id"
            ]
            conn.execute(
                "INSERT INTO animals (animal_id, user_id, species_id, nickname, hunger, is_breeding) "
                "VALUES (?, 1, ?, 'Buddy', ?, ?)",
                (animal_id, species_id, hunger, is_breeding),
            )


# ── starvation ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_starved_animal_deleted(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=0)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_starved_animals(ctx)
        with db.get_conn() as conn:
            row = conn.execute("SELECT * FROM animals WHERE animal_id='a1'").fetchone()

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
        with db.get_conn() as conn:
            row = conn.execute("SELECT * FROM animals WHERE animal_id='a1'").fetchone()

    assert row is not None


@pytest.mark.asyncio
async def test_breeding_animal_not_deleted_when_hunger_zero(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=0, is_breeding=1)

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _check_starved_animals(ctx)
        with db.get_conn() as conn:
            row = conn.execute("SELECT * FROM animals WHERE animal_id='a1'").fetchone()

    assert row is not None  # breeding animals are exempt from starvation


# ── hunger decay ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decay_reduces_hunger(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=100)

    with patch("db.DATABASE_PATH", temp_db):
        await _decay_stats()
        with db.get_conn() as conn:
            animal = conn.execute("SELECT hunger FROM animals WHERE animal_id='a1'").fetchone()
        # Hunger should have dropped by hunger_decay (varies by species, >= 1)
        assert animal["hunger"] < 100


@pytest.mark.asyncio
async def test_decay_does_not_go_below_zero(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=0)

    with patch("db.DATABASE_PATH", temp_db):
        await _decay_stats()
        with db.get_conn() as conn:
            animal = conn.execute("SELECT hunger FROM animals WHERE animal_id='a1'").fetchone()

    assert animal["hunger"] == 0


@pytest.mark.asyncio
async def test_breeding_animals_not_decayed(temp_db):
    _insert_user_and_animal(temp_db, "a1", hunger=80, is_breeding=1)

    with patch("db.DATABASE_PATH", temp_db):
        await _decay_stats()
        with db.get_conn() as conn:
            animal = conn.execute("SELECT hunger FROM animals WHERE animal_id='a1'").fetchone()

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
        # Mark alerted=20 first to simulate threshold-20 already fired
        with db.get_conn() as conn:
            conn.execute("UPDATE animals SET hunger_alerted = 20 WHERE animal_id = 'a1'")

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
        with db.get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, group_chat_id) VALUES (1, 'alice', -100)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, group_chat_id) VALUES (2, 'bob', -100)"
            )
            species_id = conn.execute("SELECT species_id FROM species LIMIT 1").fetchone()[
                "species_id"
            ]
            conn.execute(
                "INSERT INTO animals (animal_id, user_id, species_id) VALUES ('a1', 1, ?)",
                (species_id,),
            )
            conn.execute(
                "INSERT INTO animals (animal_id, user_id, species_id) VALUES ('b1', 2, ?)",
                (species_id,),
            )
            old_time = (
                datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                - datetime.timedelta(minutes=30)
            ).isoformat()
            conn.execute(
                "INSERT INTO trades (proposer_id, recipient_id, proposer_animal_id, recipient_animal_id, created_at, status) "
                "VALUES (1, 2, 'a1', 'b1', ?, 'pending')",
                (old_time,),
            )

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    with patch("db.DATABASE_PATH", temp_db):
        await _cleanup_expired_trades(ctx)
        with db.get_conn() as conn:
            trade = conn.execute("SELECT status FROM trades LIMIT 1").fetchone()

    assert trade["status"] == "expired"
    ctx.bot.send_message.assert_called_once()
