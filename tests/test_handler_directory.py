from handlers.directory import render_directory


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
