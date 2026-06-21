import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.directory import render_directory, render_directory_page
from handlers.directory import directory_command, directory_page_callback
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _sp(species_id, name, emoji, rarity, habitat):
    return {
        "species_id": species_id,
        "name": name,
        "emoji": emoji,
        "rarity": rarity,
        "habitat": habitat,
    }


WOODLAND = [
    _sp(1, "Mouse", "🐭", "common", "woodland"),
    _sp(2, "Snail", "🐌", "common", "woodland"),
    _sp(3, "Bunny", "🐰", "rare", "woodland"),
]
SAVANNA = [
    _sp(4, "Hamster", "🐹", "common", "savanna"),
    _sp(5, "Lion", "🦁", "epic", "savanna"),
]
ALL_SPECIES = WOODLAND + SAVANNA


def test_header_shows_total_and_discovered_counts():
    text = render_directory(ALL_SPECIES, {1, 4})
    assert "2/5 discovered" in text


def test_no_owned_shows_all_dots():
    text = render_directory(ALL_SPECIES, set())
    assert "0/5 discovered" in text
    assert "✅" not in text
    assert text.count("·") == len(ALL_SPECIES)


def test_all_owned_shows_all_checkmarks():
    owned = {sp["species_id"] for sp in ALL_SPECIES}
    text = render_directory(ALL_SPECIES, owned)
    assert f"{len(ALL_SPECIES)}/{len(ALL_SPECIES)} discovered" in text
    assert "·" not in text
    assert text.count("✅") == len(ALL_SPECIES)


def test_partial_ownership_correct_marks():
    text = render_directory(ALL_SPECIES, {1, 3})
    # Mouse and Bunny owned
    lines = text.splitlines()
    mouse_line = next(line for line in lines if "Mouse" in line)
    snail_line = next(line for line in lines if "Snail" in line)
    bunny_line = next(line for line in lines if "Bunny" in line)
    assert "✅" in mouse_line
    assert "·" in snail_line
    assert "✅" in bunny_line


def test_per_habitat_count_shown():
    text = render_directory(ALL_SPECIES, {1, 2})
    # Woodland: 2 owned out of 3
    assert "Woodland* — 2/3" in text
    # Savanna: 0 owned out of 2
    assert "Savanna* — 0/2" in text


def test_habitats_with_no_species_are_omitted():
    # Only woodland species in input — tundra, aquatic etc. should not appear
    text = render_directory(WOODLAND, set())
    assert "Tundra" not in text
    assert "Aquatic" not in text
    assert "Woodland" in text


def test_species_sorted_by_rarity_within_habitat():
    text = render_directory(WOODLAND, set())
    lines = text.splitlines()
    hab_start = next(i for i, line in enumerate(lines) if "Woodland" in line)
    habitat_lines = [
        line for line in lines[hab_start + 1 :] if line.strip() and not line.startswith("🌲")
    ]
    # common species (Mouse, Snail) should appear before rare (Bunny)
    names_in_order = [
        line for line in habitat_lines if any(n in line for n in ("Mouse", "Snail", "Bunny"))
    ]
    bunny_idx = next(i for i, line in enumerate(names_in_order) if "Bunny" in line)
    mouse_idx = next(i for i, line in enumerate(names_in_order) if "Mouse" in line)
    assert mouse_idx < bunny_idx


def test_rarity_squares_present():
    text = render_directory(ALL_SPECIES, set())
    assert "⬜" in text  # common
    assert "🟦" in text  # rare
    assert "🟪" in text  # epic


def test_empty_species_list():
    text = render_directory([], set())
    assert "0/0 discovered" in text


# ── render_directory_page ─────────────────────────────────────────────────────


def test_render_directory_page_shows_page_header():
    text, keys = render_directory_page(ALL_SPECIES, set(), 0)
    assert "Animal Directory" in text
    assert len(keys) > 0


def test_render_directory_page_clamps_page_below_zero():
    text, keys = render_directory_page(ALL_SPECIES, set(), -5)
    assert "Animal Directory" in text


def test_render_directory_page_clamps_page_above_max():
    _, keys = render_directory_page(ALL_SPECIES, set(), 0)
    text, _ = render_directory_page(ALL_SPECIES, set(), 9999)
    assert "Animal Directory" in text


def test_render_directory_page_empty_species_shows_no_species():
    text, keys = render_directory_page([], set(), 0)
    assert "No species found" in text
    assert keys == []


def test_render_directory_page_habitat_discovery_count():
    text, _ = render_directory_page(WOODLAND, {1}, 0)
    assert "1/3" in text


# ── directory_command ─────────────────────────────────────────────────────────


def _make_update_cmd():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock(user_data={})
    return update, ctx


@pytest.mark.asyncio
async def test_directory_command_unregistered_user():
    update, ctx = _make_update_cmd()
    with patch("handlers.directory.db.get_user", return_value=None):
        await directory_command(update, ctx)
    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_directory_command_sends_page():
    update, ctx = _make_update_cmd()
    with patch("handlers.directory.db.get_user", return_value=make_row(user_id=1)), patch(
        "handlers.directory.db.get_all_species", return_value=ALL_SPECIES
    ), patch("handlers.directory.db.get_owned_species_ids", return_value={1}):
        await directory_command(update, ctx)
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "Animal Directory" in text


# ── directory_page_callback ───────────────────────────────────────────────────


def _make_callback(user_id=1, owner_id=1, page=0):
    query = MagicMock()
    query.from_user.id = user_id
    query.data = f"dir_page_{owner_id}_{page}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query, MagicMock()


@pytest.mark.asyncio
async def test_directory_page_callback_wrong_user():
    update, query, ctx = _make_callback(user_id=999, owner_id=1, page=0)
    await directory_page_callback(update, ctx)
    # callback calls answer() once up-front, then again with show_alert for the wrong-user guard
    assert query.answer.call_count == 2
    last_call = query.answer.call_args_list[-1]
    assert last_call[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_directory_page_callback_shows_page():
    update, query, ctx = _make_callback(user_id=1, owner_id=1, page=0)
    with patch("handlers.directory.db.get_all_species", return_value=ALL_SPECIES), patch(
        "handlers.directory.db.get_owned_species_ids", return_value=set()
    ):
        await directory_page_callback(update, ctx)
    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args[0][0]
    assert "Animal Directory" in text
