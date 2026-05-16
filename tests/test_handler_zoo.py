from unittest.mock import MagicMock, patch
from handlers.zoo import render_zoo


def _make_animal(
    animal_id="a1",
    user_id=1,
    species_id=1,
    species_name="Mouse",
    emoji="🐭",
    rarity="common",
    hunger=75,
    nickname=None,
    is_breeding=0,
):
    return {
        "animal_id": animal_id,
        "user_id": user_id,
        "species_id": species_id,
        "species_name": species_name,
        "emoji": emoji,
        "rarity": rarity,
        "hunger": hunger,
        "nickname": nickname,
        "is_breeding": is_breeding,
        "hunger_decay": 3,
        "caught_at": "2026-01-01T00:00:00",
    }


def _mock_breed_conn(breeding_pairs=None):
    """Return a mock db.get_conn() that returns given breeding pairs."""
    rows = []
    for pa, pb in breeding_pairs or []:
        row = MagicMock()
        row.__getitem__ = MagicMock(
            side_effect=lambda k, _pa=pa, _pb=pb: _pa if k == "parent_a" else _pb
        )
        rows.append(row)

    inner = MagicMock()
    inner.execute.return_value.fetchall.return_value = rows
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


# ── render_zoo ────────────────────────────────────────────────────────────────


def test_render_zoo_empty():
    text = render_zoo("Alice", [], 100, 0)
    assert "Empty" in text
    assert "100" in text  # coins shown


def test_render_zoo_shows_position_and_hunger():
    animals = [_make_animal(hunger=75, nickname="Squeaky")]
    with patch("handlers.zoo.db.get_conn", return_value=_mock_breed_conn()):
        text = render_zoo("Alice", animals, 200, 5)

    assert "#1 Squeaky — 🍖 75" in text


def test_render_zoo_uses_species_name_when_no_nickname():
    animals = [_make_animal(hunger=60, nickname=None, species_name="Mouse")]
    with patch("handlers.zoo.db.get_conn", return_value=_mock_breed_conn()):
        text = render_zoo("Bob", animals, 50, 0)

    assert "#1 Mouse — 🍖 60" in text


def test_render_zoo_no_happiness_shown():
    animals = [_make_animal(hunger=80, nickname="Buddy")]
    with patch("handlers.zoo.db.get_conn", return_value=_mock_breed_conn()):
        text = render_zoo("Alice", animals, 100, 0)

    assert "happiness" not in text.lower()
    assert "😊" not in text
    assert "😢" not in text


def test_render_zoo_breeding_lock_shown():
    animal = _make_animal(animal_id="a1", nickname="Fido", is_breeding=0)
    with patch(
        "handlers.zoo.db.get_conn", return_value=_mock_breed_conn(breeding_pairs=[("a1", "a2")])
    ):
        text = render_zoo("Alice", [animal], 100, 0)

    assert "🔒" in text


def test_render_zoo_non_breeding_has_no_lock():
    animal = _make_animal(animal_id="a1", nickname="Fido", is_breeding=0)
    with patch("handlers.zoo.db.get_conn", return_value=_mock_breed_conn()):
        text = render_zoo("Alice", [animal], 100, 0)

    assert "🔒" not in text


def test_render_zoo_groups_same_species():
    animals = [
        _make_animal(animal_id="a1", species_id=1, species_name="Mouse", emoji="🐭", nickname="M1"),
        _make_animal(animal_id="a2", species_id=1, species_name="Mouse", emoji="🐭", nickname="M2"),
        _make_animal(animal_id="a3", species_id=2, species_name="Frog", emoji="🐸", nickname="F1"),
    ]
    with patch("handlers.zoo.db.get_conn", return_value=_mock_breed_conn()):
        text = render_zoo("Alice", animals, 100, 0)

    # ×2 count shown for Mouse group
    assert "×2" in text
    # Both positions exist
    assert "#1 M1" in text
    assert "#2 M2" in text
    assert "#3 F1" in text


def test_render_zoo_position_numbers_sequential():
    animals = [
        _make_animal(animal_id="a1", nickname="One"),
        _make_animal(animal_id="a2", species_id=2, species_name="Frog", emoji="🐸", nickname="Two"),
        _make_animal(
            animal_id="a3", species_id=3, species_name="Cat", emoji="🐱", nickname="Three"
        ),
    ]
    with patch("handlers.zoo.db.get_conn", return_value=_mock_breed_conn()):
        text = render_zoo("Alice", animals, 100, 0)

    assert "#1 One" in text
    assert "#2 Two" in text
    assert "#3 Three" in text


def test_render_zoo_shows_coins():
    animals = [_make_animal(nickname="X")]
    with patch("handlers.zoo.db.get_conn", return_value=_mock_breed_conn()):
        text = render_zoo("Alice", animals, 999, 0)

    assert "999" in text
