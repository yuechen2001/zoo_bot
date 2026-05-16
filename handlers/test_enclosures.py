import pytest
from species_data import HABITATS, ENCLOSURE_LEVELS, MAX_ENCLOSURE_LEVEL


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
