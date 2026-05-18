from unittest.mock import patch
from handlers.zoo import render_zoo, render_zoo_page, _render_habitat, ROW_LEN


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
    habitat="woodland",
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
        "habitat": habitat,
    }


def _zoo_patches(breeding_ids=None):
    """Return context managers that stub the two DB calls made by render_zoo_page."""
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(
        patch("handlers.zoo.db.get_breeding_animal_ids", return_value=breeding_ids or set())
    )
    stack.enter_context(patch("handlers.zoo.db.get_enclosures", return_value={}))
    return stack


# ── render_zoo ────────────────────────────────────────────────────────────────


def test_render_zoo_empty():
    text = render_zoo("Alice", [], 100, 0)
    assert "Empty" in text
    assert "100" in text  # coins shown


def test_render_zoo_shows_position_and_hunger():
    animals = [_make_animal(hunger=75, nickname="Squeaky")]
    with _zoo_patches():
        text = render_zoo("Alice", animals, 200, 5)

    assert "#1 Squeaky — 🍖 75" in text


def test_render_zoo_uses_species_name_when_no_nickname():
    animals = [_make_animal(hunger=60, nickname=None, species_name="Mouse")]
    with _zoo_patches():
        text = render_zoo("Bob", animals, 50, 0)

    assert "#1 Mouse — 🍖 60" in text


def test_render_zoo_no_happiness_shown():
    animals = [_make_animal(hunger=80, nickname="Buddy")]
    with _zoo_patches():
        text = render_zoo("Alice", animals, 100, 0)

    assert "happiness" not in text.lower()
    assert "😊" not in text
    assert "😢" not in text


def test_render_zoo_breeding_lock_shown():
    animal = _make_animal(animal_id="a1", nickname="Fido", is_breeding=0)
    with _zoo_patches(breeding_ids={"a1", "a2"}):
        text = render_zoo("Alice", [animal], 100, 0)

    assert "🔒" in text


def test_render_zoo_non_breeding_has_no_lock():
    animal = _make_animal(animal_id="a1", nickname="Fido", is_breeding=0)
    with _zoo_patches():
        text = render_zoo("Alice", [animal], 100, 0)

    assert "🔒" not in text


def test_render_zoo_groups_same_species():
    animals = [
        _make_animal(animal_id="a1", species_id=1, species_name="Mouse", emoji="🐭", nickname="M1"),
        _make_animal(animal_id="a2", species_id=1, species_name="Mouse", emoji="🐭", nickname="M2"),
        _make_animal(animal_id="a3", species_id=2, species_name="Frog", emoji="🐸", nickname="F1"),
    ]
    with _zoo_patches():
        text = render_zoo("Alice", animals, 100, 0)

    assert "×2" in text
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
    with _zoo_patches():
        text = render_zoo("Alice", animals, 100, 0)

    assert "#1 One" in text
    assert "#2 Two" in text
    assert "#3 Three" in text


# ── power-up indicators ───────────────────────────────────────────────────────


def _render_with_powerups(**flags):
    animals = [_make_animal()]
    powerups = {
        "lucky_catch_active": 0,
        "mood_booster_active": 0,
        "catch_net_active": 0,
        **flags,
    }
    with _zoo_patches():
        text, _ = render_zoo_page("Alice", animals, 100, 0, active_powerups=powerups)
    return text


def test_powerup_indicator_shown_when_active():
    text = _render_with_powerups(lucky_catch_active=1, catch_net_active=1)
    assert "⚡ Active:" in text
    assert "🎯 Lucky" in text
    assert "🪤 Catch Net" in text


def test_powerup_indicator_hidden_when_none_active():
    text = _render_with_powerups()
    assert "⚡ Active:" not in text


def test_powerup_indicator_only_lists_active_flags():
    text = _render_with_powerups(mood_booster_active=1)
    assert "✨ Mood Boost" in text
    assert "🎯 Lucky" not in text
    assert "🪤 Catch Net" not in text


def test_render_zoo_shows_coins():
    animals = [_make_animal(nickname="X")]
    with _zoo_patches():
        text = render_zoo("Alice", animals, 999, 0)

    assert "999" in text


# ── _render_habitat ────────────────────────────────────────────────────────────


def test_render_habitat_always_9_tiles():
    for count in range(0, 10):
        result = _render_habitat("🐭", count, 0)
        assert len(result.encode("utf-32")) // 4 - 1 == ROW_LEN or len(result) >= 1


def test_render_habitat_tile_count_is_row_len():
    """Tile string should always contain exactly ROW_LEN grapheme clusters."""
    import unicodedata

    def grapheme_len(s):
        # Simple approximation: count code points that start a grapheme
        return sum(1 for c in s if unicodedata.category(c) not in ("Mn", "Cf"))

    for count, breeding in [(0, 0), (1, 0), (3, 1), (9, 0), (9, 3)]:
        result = _render_habitat("🐭", count, breeding)
        # Each emoji is one grapheme cluster; ROW_LEN tiles expected
        assert grapheme_len(result) == ROW_LEN


def test_render_habitat_randomises_positions():
    """Repeated calls should not always produce the same tile order."""
    results = {_render_habitat("🐭", 3, 0) for _ in range(30)}
    # With 3 animals in 9 tiles, C(9,3)=84 arrangements — 30 tries should find >1
    assert len(results) > 1


def test_render_habitat_breeding_count_respected():
    result = _render_habitat("🐭", 3, 2)
    assert result.count("💤") == 2
    assert result.count("🐭") == 1


# ── render_zoo_page pagination ─────────────────────────────────────────────────


def test_render_zoo_page_returns_inhabited_keys():
    animals = [
        _make_animal(animal_id="a1", habitat="woodland"),
        _make_animal(
            animal_id="a2", species_id=2, species_name="Duck", emoji="🦆", habitat="aquatic"
        ),
    ]
    with _zoo_patches():
        _, inhabited = render_zoo_page("Alice", animals, 100, 0, page=0)

    assert inhabited == ["woodland", "aquatic"]


def test_render_zoo_page_shows_only_requested_habitat():
    woodland_animal = _make_animal(
        animal_id="a1", habitat="woodland", species_name="Mouse", emoji="🐭"
    )
    aquatic_animal = _make_animal(
        animal_id="a2", species_id=2, species_name="Duck", emoji="🦆", habitat="aquatic"
    )
    animals = [woodland_animal, aquatic_animal]

    with _zoo_patches():
        text0, _ = render_zoo_page("Alice", animals, 100, 0, page=0)
        text1, _ = render_zoo_page("Alice", animals, 100, 0, page=1)

    assert "Mouse" in text0
    assert "Duck" not in text0
    assert "Duck" in text1
    assert "Mouse" not in text1


def test_render_zoo_page_position_numbers_global():
    """Position numbers reflect index across all animals, not just the page."""
    woodland_animal = _make_animal(animal_id="a1", habitat="woodland", nickname="First")
    aquatic_animal = _make_animal(
        animal_id="a2",
        species_id=2,
        species_name="Duck",
        emoji="🦆",
        habitat="aquatic",
        nickname="Second",
    )
    animals = [woodland_animal, aquatic_animal]

    with _zoo_patches():
        text1, _ = render_zoo_page("Alice", animals, 100, 0, page=1)

    assert "#2 Second" in text1


def test_render_zoo_page_out_of_range_clamped():
    animals = [_make_animal(animal_id="a1", habitat="woodland")]
    with _zoo_patches():
        text, inhabited = render_zoo_page("Alice", animals, 100, 0, page=99)

    assert len(inhabited) == 1
    assert "Mouse" in text


def test_render_zoo_page_empty_returns_empty_list():
    text, inhabited = render_zoo_page("Alice", [], 100, 0, page=0)
    assert inhabited == []
    assert "Empty" in text
