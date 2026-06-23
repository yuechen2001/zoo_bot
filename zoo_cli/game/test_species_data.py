import pytest
from game.species_data import (
    SPECIES,
    RARITY_ORDER,
    ENCOUNTER_WEIGHTS,
    ENCLOSURE_LEVELS,
    MAX_ENCLOSURE_LEVEL,
    get_breed_params,
)


class TestGetBreedParams:
    def test_common_common(self):
        assert get_breed_params("common", "common") == {"cost": 50, "hours": 0.5}

    def test_common_rare(self):
        assert get_breed_params("common", "rare") == {"cost": 120, "hours": 1.5}

    def test_rare_rare(self):
        assert get_breed_params("rare", "rare") == {"cost": 200, "hours": 3.0}

    def test_common_epic(self):
        assert get_breed_params("common", "epic") == {"cost": 250, "hours": 2.0}

    def test_epic_epic(self):
        assert get_breed_params("epic", "epic") == {"cost": 400, "hours": 8.0}

    def test_legendary_legendary(self):
        assert get_breed_params("legendary", "legendary") == {"cost": 800, "hours": 16.0}

    def test_symmetry_rare_common(self):
        assert get_breed_params("rare", "common") == get_breed_params("common", "rare")

    def test_symmetry_legendary_epic(self):
        assert get_breed_params("legendary", "epic") == get_breed_params("epic", "legendary")

    def test_all_valid_rarity_pairs_are_in_table(self):
        from itertools import combinations_with_replacement
        from game.species_data import RARITY_ORDER

        for a, b in combinations_with_replacement(RARITY_ORDER, 2):
            result = get_breed_params(a, b)
            assert "cost" in result and "hours" in result


class TestEncounterWeights:
    def test_weights_sum_to_100(self):
        assert sum(ENCOUNTER_WEIGHTS.values()) == 100

    def test_all_four_rarities_present(self):
        assert set(ENCOUNTER_WEIGHTS.keys()) == {"common", "rare", "epic", "legendary"}


class TestRarityOrder:
    def test_order_is_correct(self):
        assert RARITY_ORDER == ["common", "rare", "epic", "legendary"]


class TestSpeciesDataFix6:
    def test_giraffe_exists(self):
        names = [s["name"] for s in SPECIES]
        assert "Giraffe" in names

    def test_elephant_exists(self):
        names = [s["name"] for s in SPECIES]
        assert "Elephant" in names

    def test_giraffe_is_legendary(self):
        giraffe = next(s for s in SPECIES if s["name"] == "Giraffe")
        assert giraffe["rarity"] == "legendary"

    def test_elephant_is_legendary(self):
        elephant = next(s for s in SPECIES if s["name"] == "Elephant")
        assert elephant["rarity"] == "legendary"

    def test_epic_catch_cost_is_80(self):
        epics = [s for s in SPECIES if s["rarity"] == "epic" and s["catch_rate"] > 0]
        assert len(epics) > 0
        for s in epics:
            assert (
                s["catch_cost"] == 80
            ), f"{s['name']} has catch_cost={s['catch_cost']}, expected 80"

    def test_legendary_catch_cost_is_200(self):
        legendaries = [s for s in SPECIES if s["rarity"] == "legendary" and s["catch_rate"] > 0]
        assert len(legendaries) > 0
        for s in legendaries:
            assert (
                s["catch_cost"] == 200
            ), f"{s['name']} has catch_cost={s['catch_cost']}, expected 200"

    def test_all_species_have_required_fields(self):
        required = {
            "name",
            "emoji",
            "rarity",
            "catch_rate",
            "catch_cost",
            "hunger_decay",
            "breed_time_hrs",
        }
        for s in SPECIES:
            missing = required - s.keys()
            assert not missing, f"{s['name']} is missing fields: {missing}"


class TestEnclosureLevels:
    def test_all_levels_present(self):
        assert set(ENCLOSURE_LEVELS.keys()) == {1, 2, 3, 4, 5, 6, 7, 8}

    def test_max_enclosure_level_is_8(self):
        assert MAX_ENCLOSURE_LEVEL == 8

    def test_all_levels_have_required_keys(self):
        required = {
            "capacity",
            "coins_per_animal_hr",
            "breed_bonus",
            "catch_rate_bonus",
            "upgrade_cost",
        }
        for level, stats in ENCLOSURE_LEVELS.items():
            missing = required - stats.keys()
            assert not missing, f"Level {level} missing keys: {missing}"

    def test_levels_1_to_5_have_zero_catch_rate_bonus(self):
        for level in range(1, 6):
            assert (
                ENCLOSURE_LEVELS[level]["catch_rate_bonus"] == 0.0
            ), f"Level {level} should have catch_rate_bonus 0.0"

    def test_levels_6_to_8_have_positive_catch_rate_bonus(self):
        for level in range(6, 9):
            assert (
                ENCLOSURE_LEVELS[level]["catch_rate_bonus"] > 0.0
            ), f"Level {level} should have positive catch_rate_bonus"

    def test_catch_rate_bonus_increases_with_level(self):
        bonuses = [ENCLOSURE_LEVELS[lv]["catch_rate_bonus"] for lv in range(6, 9)]
        assert bonuses == sorted(bonuses)
        assert bonuses[0] == pytest.approx(0.05)
        assert bonuses[1] == pytest.approx(0.10)
        assert bonuses[2] == pytest.approx(0.15)

    def test_capacity_increases_with_level(self):
        caps = [ENCLOSURE_LEVELS[lv]["capacity"] for lv in range(1, 9)]
        assert caps == sorted(caps)

    def test_level_1_upgrade_cost_is_zero(self):
        assert ENCLOSURE_LEVELS[1]["upgrade_cost"] == 0
