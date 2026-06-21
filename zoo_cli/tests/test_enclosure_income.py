import pytest
import unittest.mock as mock
from game.species_data import ENCLOSURE_LEVELS


@pytest.fixture
def db(tmp_path):
    import db as db_module

    db_path = str(tmp_path / "test.db")
    with mock.patch.object(db_module, "DATABASE_PATH", db_path):
        db_module.init_db()
        yield db_module


@pytest.fixture
def user_with_animals(db):
    db.ensure_user(1, "tester", 100)
    db.give_starter_enclosures(1)
    woodland_species = next(s for s in db.get_all_species() if s["habitat"] == "woodland")
    db.add_animal("a1", 1, woodland_species["species_id"])
    db.add_animal("a2", 1, woodland_species["species_id"])
    return db


class TestEnclosureIncome:
    def test_income_zero_at_level_1(self, user_with_animals):
        db = user_with_animals
        # Level 1 has 0 coins_per_animal_hr — no income expected
        assert ENCLOSURE_LEVELS[1]["coins_per_animal_hr"] == 0

        enclosures = db.get_enclosures(1)
        total = 0
        for habitat, level in enclosures.items():
            rate = ENCLOSURE_LEVELS[level]["coins_per_animal_hr"]
            count = db.get_animal_count_by_habitat(1, habitat)
            total += rate * count

        assert total == 0

    def test_income_scales_with_animals(self, user_with_animals):
        db = user_with_animals
        db.set_enclosure_level(1, "woodland", 2)
        rate = ENCLOSURE_LEVELS[2]["coins_per_animal_hr"]
        animal_count = db.get_animal_count_by_habitat(1, "woodland")
        expected = rate * animal_count

        assert expected == rate * 2

    def test_income_only_from_level_2_plus(self, user_with_animals):
        db = user_with_animals
        enclosures = db.get_enclosures(1)
        earning_habitats = [
            h for h, lv in enclosures.items() if ENCLOSURE_LEVELS[lv]["coins_per_animal_hr"] > 0
        ]
        assert earning_habitats == [], "Level-1 enclosures must not earn income"


# ── _tick_enclosure_income named message ───────────────────────────────────────


@pytest.mark.asyncio
async def test_enclosure_income_sends_named_group_message():
    """Named income message groups earnings per chat, not per user."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from scheduler import _tick_enclosure_income

    user = MagicMock()
    user.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "user_id": 1,
            "group_chat_id": -100,
            "username": "alice",
        }[k]
    )
    user.get = MagicMock(side_effect=lambda k, d=None: {"username": "alice"}.get(k, d))

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()

    import datetime

    adult_caught_at = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)
    ).isoformat()
    mock_animals = [
        {"habitat": "woodland", "caught_at": adult_caught_at},
        {"habitat": "woodland", "caught_at": adult_caught_at},
    ]

    with patch("scheduler.db.get_all_users_with_animals", return_value=[user]), patch(
        "scheduler.db.get_enclosures", return_value={"woodland": 2}
    ), patch("scheduler.db.get_animals", return_value=mock_animals), patch(
        "scheduler.db.add_pending_enclosure_coins"
    ), patch(
        "scheduler.db.get_pending_enclosure_coins", return_value=6
    ):
        await _tick_enclosure_income(ctx)

    ctx.bot.send_message.assert_called_once()
    args = ctx.bot.send_message.call_args
    assert args[0][0] == -100  # sent to group
    assert "alice" in args[0][1]
    assert "Enclosure income" in args[0][1]
