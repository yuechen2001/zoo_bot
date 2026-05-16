import pytest
from unittest.mock import patch
from game.catch_engine import roll_catch, roll_encounter, pick_species
from species_data import ENCOUNTER_WEIGHTS


class TestRollCatch:
    def test_succeeds_when_random_below_rate(self):
        with patch("game.catch_engine.random.random", return_value=0.5):
            assert roll_catch(0.9) is True

    def test_fails_when_random_above_rate(self):
        with patch("game.catch_engine.random.random", return_value=0.95):
            assert roll_catch(0.9) is False

    def test_boundary_is_strict_less_than(self):
        # random < rate, not <=, so equal values fail
        with patch("game.catch_engine.random.random", return_value=0.5):
            assert roll_catch(0.5) is False

    def test_certain_catch(self):
        with patch("game.catch_engine.random.random", return_value=0.0):
            assert roll_catch(0.1) is True

    def test_impossible_catch(self):
        with patch("game.catch_engine.random.random", return_value=0.999):
            assert roll_catch(0.1) is False


class TestRollEncounter:
    def test_returns_valid_rarity(self):
        assert roll_encounter() in ENCOUNTER_WEIGHTS

    def test_distribution_within_tolerance(self):
        n = 10_000
        counts = {r: 0 for r in ENCOUNTER_WEIGHTS}
        for _ in range(n):
            counts[roll_encounter()] += 1
        total_weight = sum(ENCOUNTER_WEIGHTS.values())
        for rarity, weight in ENCOUNTER_WEIGHTS.items():
            expected = weight / total_weight
            actual = counts[rarity] / n
            assert abs(actual - expected) < 0.05, (
                f"{rarity}: expected ~{expected:.2f}, got {actual:.2f}"
            )


class TestPickSpecies:
    def test_returns_species_of_correct_rarity(self, conn):
        species = pick_species("common", conn)
        assert species is not None
        assert species["rarity"] == "common"

    def test_legendary_species_returned(self, conn):
        species = pick_species("legendary", conn)
        assert species is not None
        assert species["rarity"] == "legendary"

    def test_returns_none_for_unknown_rarity(self, conn):
        assert pick_species("nonexistent", conn) is None

    def test_returned_species_has_catch_rate(self, conn):
        species = pick_species("rare", conn)
        assert species is not None
        assert 0 < species["catch_rate"] <= 1.0
