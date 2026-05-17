import sys
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from species_data import HABITATS, ENCLOSURE_LEVELS, MAX_ENCLOSURE_LEVEL

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


@pytest.fixture
def db(tmp_path):
    """Minimal in-memory DB with users, species, animals, and user_enclosures tables."""
    import db as db_module

    db_path = str(tmp_path / "test.db")
    original = db_module.DATABASE_PATH

    import unittest.mock as mock

    with mock.patch.object(db_module, "DATABASE_PATH", db_path):
        db_module.init_db()
        yield db_module

    # restore
    db_module.DATABASE_PATH = original


@pytest.fixture
def user(db):
    db.ensure_user(1, "tester", 100)
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET coins = 10000 WHERE user_id = 1")
    return db.get_user(1)


class TestGiveStarterEnclosures:
    def test_creates_all_habitats_at_level_1(self, db, user):
        db.give_starter_enclosures(1)
        enclosures = db.get_enclosures(1)
        assert set(enclosures.keys()) == set(HABITATS.keys())
        assert all(level == 1 for level in enclosures.values())

    def test_idempotent(self, db, user):
        db.give_starter_enclosures(1)
        db.give_starter_enclosures(1)
        enclosures = db.get_enclosures(1)
        assert len(enclosures) == len(HABITATS)


class TestGetEnclosureLevel:
    def test_returns_1_when_no_enclosure(self, db, user):
        assert db.get_enclosure_level(1, "woodland") == 1

    def test_returns_stored_level(self, db, user):
        db.give_starter_enclosures(1)
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE user_enclosures SET level = 3 WHERE user_id = 1 AND habitat = 'woodland'"
            )
        assert db.get_enclosure_level(1, "woodland") == 3


class TestUpgradeEnclosure:
    def test_level_increments_and_coins_deducted(self, db, user):
        db.give_starter_enclosures(1)
        before_coins = db.get_user(1)["coins"]
        cost = ENCLOSURE_LEVELS[2]["upgrade_cost"]

        result = db.upgrade_enclosure(1, "woodland")

        assert result == "ok"
        assert db.get_enclosure_level(1, "woodland") == 2
        assert db.get_user(1)["coins"] == before_coins - cost

    def test_max_level_rejected(self, db, user):
        db.give_starter_enclosures(1)
        with db.get_conn() as conn:
            conn.execute(
                f"UPDATE user_enclosures SET level = {MAX_ENCLOSURE_LEVEL} "
                "WHERE user_id = 1 AND habitat = 'woodland'"
            )
        result = db.upgrade_enclosure(1, "woodland")
        assert result == "max_level"

    def test_insufficient_coins_rejected(self, db, user):
        db.give_starter_enclosures(1)
        with db.get_conn() as conn:
            conn.execute("UPDATE users SET coins = 0 WHERE user_id = 1")
        result = db.upgrade_enclosure(1, "woodland")
        assert result == "insufficient_coins"
        assert db.get_enclosure_level(1, "woodland") == 1

    def test_coins_not_deducted_on_failure(self, db, user):
        db.give_starter_enclosures(1)
        with db.get_conn() as conn:
            conn.execute("UPDATE users SET coins = 0 WHERE user_id = 1")
        db.upgrade_enclosure(1, "woodland")
        assert db.get_user(1)["coins"] == 0


class TestGetAnimalCountByHabitat:
    def test_zero_when_no_animals(self, db, user):
        count = db.get_animal_count_by_habitat(1, "woodland")
        assert count == 0

    def test_counts_only_matching_habitat(self, db, user):
        with db.get_conn() as conn:
            woodland_species = conn.execute(
                "SELECT species_id FROM species WHERE habitat = 'woodland' LIMIT 1"
            ).fetchone()
            aquatic_species = conn.execute(
                "SELECT species_id FROM species WHERE habitat = 'aquatic' LIMIT 1"
            ).fetchone()

        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO animals (animal_id, user_id, species_id) VALUES ('a1', 1, ?)",
                (woodland_species["species_id"],),
            )
            conn.execute(
                "INSERT INTO animals (animal_id, user_id, species_id) VALUES ('a2', 1, ?)",
                (woodland_species["species_id"],),
            )
            conn.execute(
                "INSERT INTO animals (animal_id, user_id, species_id) VALUES ('a3', 1, ?)",
                (aquatic_species["species_id"],),
            )

        assert db.get_animal_count_by_habitat(1, "woodland") == 2
        assert db.get_animal_count_by_habitat(1, "aquatic") == 1
        assert db.get_animal_count_by_habitat(1, "savanna") == 0


# ── /enclosures collect ────────────────────────────────────────────────────────


def _make_update_cmd(args=None):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args or []
    return update, ctx


def _make_user_row(**kw):
    defaults = {
        "user_id": 1,
        "coins": 100,
        "pending_enclosure_coins": 0,
        "autofeed_threshold": None,
        "autofeed_max_coins": None,
        "streak_windows": 0,
        "active_title": None,
    }
    return make_row(**{**defaults, **kw})


@pytest.mark.asyncio
async def test_collect_nothing_pending():
    from handlers.enclosures import enclosures_command

    update, ctx = _make_update_cmd(args=["collect"])
    with patch("handlers.enclosures.db.get_user", return_value=_make_user_row()), patch(
        "handlers.enclosures.db.collect_enclosure_coins", return_value=0
    ):
        await enclosures_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "nothing" in reply.lower() or "no" in reply.lower() or "builds" in reply.lower()


@pytest.mark.asyncio
async def test_collect_credits_pending_coins():
    from handlers.enclosures import enclosures_command

    update, ctx = _make_update_cmd(args=["collect"])
    with patch("handlers.enclosures.db.get_user", return_value=_make_user_row(coins=100)), patch(
        "handlers.enclosures.db.collect_enclosure_coins", return_value=42
    ), patch("handlers.enclosures.db.get_user", return_value=_make_user_row(coins=142)):
        await enclosures_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "42" in reply or "Collected" in reply
