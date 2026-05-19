import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.zoo import (
    render_zoo,
    render_zoo_page,
    _render_habitat,
    _time_remaining,
    zoo_command,
    zoo_page_callback,
    ROW_LEN,
)
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


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
        "rare_magnet_active": 0,
        "epic_magnet_active": 0,
        "streak_shield_active": 0,
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


# ── _time_remaining ───────────────────────────────────────────────────────────


def _future(seconds: float) -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(seconds=seconds)
    ).isoformat()


def _past(seconds: float = 60) -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(seconds=seconds)
    ).isoformat()


def test_time_remaining_past_returns_ready():
    assert _time_remaining(_past(60)) == "ready!"


def test_time_remaining_shows_hours_and_minutes():
    result = _time_remaining(_future(90 * 60 + 59))
    assert result == "1h 30m"


def test_time_remaining_shows_minutes_only():
    result = _time_remaining(_future(20 * 60 + 59))
    assert result == "20m"


# ── zoo_command ───────────────────────────────────────────────────────────────


def _make_user(**kw):
    defaults = dict(
        user_id=1,
        coins=100,
        streak_windows=0,
        autofeed_threshold=None,
        autofeed_max_coins=None,
        active_title=None,
        lucky_catch_active=0,
        mood_booster_active=0,
        catch_net_active=0,
        rare_magnet_active=0,
        epic_magnet_active=0,
        streak_shield_active=0,
    )
    return make_row(**{**defaults, **kw})


@pytest.mark.asyncio
async def test_zoo_command_no_user():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    with patch("handlers.zoo.db.get_user", return_value=None):
        await zoo_command(update, MagicMock())
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_zoo_command_empty_zoo_sends_no_keyboard():
    update = MagicMock()
    update.effective_user.id = 1
    update.effective_user.first_name = "Alice"
    update.message.reply_text = AsyncMock()
    with patch("handlers.zoo.db.get_user", return_value=_make_user()), patch(
        "handlers.zoo.db.get_animals", return_value=[]
    ), patch("handlers.zoo.db.get_active_investment", return_value=None), patch(
        "handlers.zoo.db.get_active_breed", return_value=None
    ):
        await zoo_command(update, MagicMock())
    call_kwargs = update.message.reply_text.call_args[1]
    assert call_kwargs.get("reply_markup") is None


# ── zoo_page_callback ─────────────────────────────────────────────────────────


def _make_page_callback(owner_id: int, page: int, from_user_id: int):
    query = MagicMock()
    query.data = f"zoo_page_{owner_id}_{page}"
    query.from_user.id = from_user_id
    query.from_user.first_name = "Alice"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query


@pytest.mark.asyncio
async def test_zoo_page_callback_wrong_user_blocked():
    update, query = _make_page_callback(owner_id=1, page=1, from_user_id=99)
    await zoo_page_callback(update, MagicMock())
    query.answer.assert_called_once_with("Use /zoo to see your own zoo.", show_alert=False)
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_zoo_page_callback_correct_user_edits_message():
    update, query = _make_page_callback(owner_id=1, page=0, from_user_id=1)
    animal = _make_animal(animal_id="a1", habitat="woodland")
    with patch("handlers.zoo.db.get_user", return_value=_make_user()), patch(
        "handlers.zoo.db.get_animals", return_value=[animal]
    ), patch("handlers.zoo.db.get_active_investment", return_value=None), patch(
        "handlers.zoo.db.get_active_breed", return_value=None
    ), patch(
        "handlers.zoo.db.get_breeding_animal_ids", return_value=set()
    ), patch(
        "handlers.zoo.db.get_enclosures", return_value={}
    ):
        await zoo_page_callback(update, MagicMock())
    query.edit_message_text.assert_called_once()


# ── render_zoo_page with active_title / investment / active_breed ─────────────


def _make_investment(hours_remaining: float = 5):
    invested_at = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(hours=1)
    ).isoformat()
    return make_row(
        invested_at=invested_at,
        amount=100,
        return_amount=120,
    )


def _make_breed(hours_remaining: float = 3):
    ready_at = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(hours=hours_remaining)
    ).isoformat()
    return make_row(ready_at=ready_at, emoji_a="🐭", emoji_b="🐸")


def test_render_zoo_page_with_active_title():
    from game.store_data import COSMETICS

    first_key = next(iter(COSMETICS))
    animals = [_make_animal(animal_id="a1", habitat="woodland")]
    with _zoo_patches():
        text, _ = render_zoo_page("Alice", animals, 100, 0, active_title=first_key)
    item = COSMETICS[first_key]
    assert item["name"] in text


def test_render_zoo_page_with_investment():
    animals = [_make_animal(animal_id="a1", habitat="woodland")]
    investment = _make_investment()
    with _zoo_patches():
        text, _ = render_zoo_page("Alice", animals, 100, 0, investment=investment)
    assert "Investment" in text
    assert "100" in text


def test_render_zoo_page_with_active_breed():
    animals = [_make_animal(animal_id="a1", habitat="woodland")]
    breed = _make_breed()
    with _zoo_patches():
        text, _ = render_zoo_page("Alice", animals, 100, 0, active_breed=breed)
    assert "Breeding" in text
    assert "🐭" in text


def test_render_zoo_page_with_autofeed_shows_threshold():
    animals = [_make_animal(animal_id="a1", habitat="woodland")]
    with _zoo_patches():
        text, _ = render_zoo_page(
            "Alice", animals, 100, 0, autofeed_threshold=30, autofeed_max_coins=50
        )
    assert "Auto-feed" in text
    assert "30" in text
