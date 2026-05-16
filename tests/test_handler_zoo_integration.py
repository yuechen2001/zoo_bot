"""
Integration tests for render_zoo using a real temp DB.

These exist specifically to catch sqlite3.Row vs dict mismatches that
unit tests (which mock animals as plain dicts) cannot detect.
"""

import pytest
from unittest.mock import patch
import db
from handlers.zoo import render_zoo_page


@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch("db.DATABASE_PATH", db_path):
        db.init_db()
        yield db_path


def _insert_user_and_animal(db_path, user_id=1, nickname="Buddy", hunger=80):
    with patch("db.DATABASE_PATH", db_path):
        with db.get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, group_chat_id) VALUES (?, 'tester', -100)",
                (user_id,),
            )
            species_id = conn.execute("SELECT species_id FROM species LIMIT 1").fetchone()[
                "species_id"
            ]
            conn.execute(
                "INSERT INTO animals (animal_id, user_id, species_id, nickname, hunger) "
                "VALUES ('a1', ?, ?, ?, ?)",
                (user_id, species_id, nickname, hunger),
            )


def test_render_zoo_with_real_db_rows(temp_db):
    """sqlite3.Row objects must not be accessed via .get() — this test catches that."""
    _insert_user_and_animal(temp_db, hunger=75)
    with patch("db.DATABASE_PATH", temp_db):
        animals = db.get_animals(1)
        user = db.get_user(1)

    assert len(animals) == 1
    text, _ = render_zoo_page("Alice", animals, user["coins"], user["streak_windows"], page=0)
    assert "Alice" in text
    assert "Buddy" in text
    assert "75" in text


def test_render_zoo_empty_with_real_db(temp_db):
    with patch("db.DATABASE_PATH", temp_db):
        conn_ctx = db.get_conn()
        with conn_ctx as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (1, 'tester')")
        animals = db.get_animals(1)
        user = db.get_user(1)

    text, _ = render_zoo_page("Alice", animals, user["coins"], user["streak_windows"], page=0)
    assert "Empty" in text


def test_render_zoo_habitat_grouping_with_real_db(temp_db):
    """Animals appear under their correct habitat section."""
    _insert_user_and_animal(temp_db, hunger=90)
    with patch("db.DATABASE_PATH", temp_db):
        animals = db.get_animals(1)
        user = db.get_user(1)

    text, _ = render_zoo_page("Alice", animals, user["coins"], user["streak_windows"], page=0)
    # Habitat header must appear (the species seeded always has a habitat)
    assert animals[0]["habitat"] in (
        "woodland",
        "savanna",
        "tropical",
        "aquatic",
        "tundra",
        "mythic",
    )
    assert "Lv" in text  # enclosure level shown
