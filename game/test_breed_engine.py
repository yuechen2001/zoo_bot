import datetime
from unittest.mock import patch
from game.breed_engine import (
    calc_breed_cost,
    breed_duration_str,
    calc_breed_ready_at,
    resolve_offspring,
    _RARITY_WEIGHTS,
)
from species_data import RARITY_ORDER


def _candidates(conn):
    return lambda r: conn.execute("SELECT * FROM species WHERE rarity = ?", (r,)).fetchall()


class TestCalcBreedCost:
    def test_common_common(self):
        assert calc_breed_cost("common", "common") == 50

    def test_common_rare(self):
        assert calc_breed_cost("common", "rare") == 120

    def test_rare_rare(self):
        assert calc_breed_cost("rare", "rare") == 200

    def test_common_epic(self):
        assert calc_breed_cost("common", "epic") == 250

    def test_rare_epic(self):
        assert calc_breed_cost("rare", "epic") == 300

    def test_epic_epic(self):
        assert calc_breed_cost("epic", "epic") == 400

    def test_common_legendary(self):
        assert calc_breed_cost("common", "legendary") == 500

    def test_rare_legendary(self):
        assert calc_breed_cost("rare", "legendary") == 600

    def test_epic_legendary(self):
        assert calc_breed_cost("epic", "legendary") == 700

    def test_legendary_legendary(self):
        assert calc_breed_cost("legendary", "legendary") == 800

    def test_symmetry_common_rare(self):
        assert calc_breed_cost("rare", "common") == calc_breed_cost("common", "rare")

    def test_symmetry_epic_legendary(self):
        assert calc_breed_cost("legendary", "epic") == calc_breed_cost("epic", "legendary")


class TestBreedDurationStr:
    # At hunger=100 the modifier is 1.0× (base times used directly)
    def test_common_common_full_hunger(self):
        assert breed_duration_str("common", "common", 100, 100) == "30m"

    def test_rare_rare_full_hunger(self):
        assert breed_duration_str("rare", "rare", 100, 100) == "1h"

    def test_epic_epic_full_hunger(self):
        assert breed_duration_str("epic", "epic", 100, 100) == "2h"

    def test_legendary_legendary_full_hunger(self):
        assert breed_duration_str("legendary", "legendary", 100, 100) == "2h"

    def test_common_rare_full_hunger(self):
        assert breed_duration_str("common", "rare", 100, 100) == "45m"

    def test_legendary_legendary_zero_hunger_is_4h(self):
        # At 0 hunger modifier = 2.0× → 2h × 2 = 4h
        assert breed_duration_str("legendary", "legendary", 0, 0) == "4h"

    def test_hunger_increases_time(self):
        short = breed_duration_str("rare", "rare", 100, 100)
        long_ = breed_duration_str("rare", "rare", 0, 0)

        # Parse minutes from strings and compare
        def to_minutes(s):
            h = m = 0
            if "h" in s:
                parts = s.split("h")
                h = int(parts[0].strip())
                if parts[1].strip():
                    m = int(parts[1].replace("m", "").strip())
            else:
                m = int(s.replace("m", "").strip())
            return h * 60 + m

        assert to_minutes(long_) > to_minutes(short)


class TestCalcBreedReadyAt:
    def test_returns_future_timestamp(self):
        before = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        ts = calc_breed_ready_at("common", "common")
        dt = datetime.datetime.fromisoformat(ts)
        assert dt > before

    def test_common_common_full_hunger_approx_30m(self):
        ts = calc_breed_ready_at("common", "common", 100, 100)
        dt = datetime.datetime.fromisoformat(ts)
        delta = dt - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        assert abs(delta.total_seconds() - 30 * 60) < 5

    def test_legendary_legendary_full_hunger_approx_2h(self):
        ts = calc_breed_ready_at("legendary", "legendary", 100, 100)
        dt = datetime.datetime.fromisoformat(ts)
        delta = dt - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        assert abs(delta.total_seconds() - 2 * 3600) < 5

    def test_low_hunger_makes_longer_breed(self):
        ts_full = calc_breed_ready_at("rare", "rare", 100, 100)
        ts_empty = calc_breed_ready_at("rare", "rare", 0, 0)
        dt_full = datetime.datetime.fromisoformat(ts_full)
        dt_empty = datetime.datetime.fromisoformat(ts_empty)
        assert dt_empty > dt_full


class TestHabitatBonus:
    def test_bonus_reduces_breed_time(self):
        import datetime

        ts_no_bonus = calc_breed_ready_at("rare", "rare", 100, 100, habitat_bonus=0.0)
        ts_with_bonus = calc_breed_ready_at("rare", "rare", 100, 100, habitat_bonus=0.15)
        dt_no = datetime.datetime.fromisoformat(ts_no_bonus)
        dt_with = datetime.datetime.fromisoformat(ts_with_bonus)
        assert dt_with < dt_no

    def test_zero_bonus_no_change(self):
        import datetime

        ts1 = calc_breed_ready_at("common", "common", 100, 100, habitat_bonus=0.0)
        ts2 = calc_breed_ready_at("common", "common", 100, 100)
        dt1 = datetime.datetime.fromisoformat(ts1)
        dt2 = datetime.datetime.fromisoformat(ts2)
        assert abs((dt1 - dt2).total_seconds()) < 1

    def test_duration_str_reflects_bonus(self):
        def to_minutes(s):
            h = m = 0
            if "h" in s:
                parts = s.split("h")
                h = int(parts[0].strip())
                if parts[1].strip():
                    m = int(parts[1].replace("m", "").strip())
            else:
                m = int(s.replace("m", "").strip())
            return h * 60 + m

        no_bonus = breed_duration_str("rare", "rare", 100, 100, habitat_bonus=0.0)
        with_bonus = breed_duration_str("rare", "rare", 100, 100, habitat_bonus=0.40)
        assert to_minutes(with_bonus) < to_minutes(no_bonus)


class TestResolveOffspring:
    def test_choices_forced_to_rare_gives_rare(self, conn):
        # Force random.choices to always return "rare"
        with patch("game.breed_engine.random.choices", return_value=["rare"]):
            species_id = resolve_offspring("common", "rare", _candidates(conn))
        row = conn.execute(
            "SELECT rarity FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row["rarity"] == "rare"

    def test_choices_forced_to_common_gives_common(self, conn):
        with patch("game.breed_engine.random.choices", return_value=["common"]):
            species_id = resolve_offspring("common", "rare", _candidates(conn))
        row = conn.execute(
            "SELECT rarity FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row["rarity"] == "common"

    def test_choices_forced_to_legendary_gives_legendary(self, conn):
        with patch("game.breed_engine.random.choices", return_value=["legendary"]):
            species_id = resolve_offspring("common", "common", _candidates(conn))
        row = conn.execute(
            "SELECT rarity FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row["rarity"] == "legendary"

    def test_legendary_x_legendary_can_produce_any_rarity(self, conn):
        # Verify legendary×legendary has non-zero weight for all rarities
        from game.breed_engine import _RARITY_WEIGHTS

        weights = _RARITY_WEIGHTS[("legendary", "legendary")]
        assert all(w > 0 for w in weights)

    def test_returns_valid_species_id(self, conn):
        species_id = resolve_offspring("common", "common", _candidates(conn))
        row = conn.execute(
            "SELECT species_id FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row is not None

    def test_all_rarity_pairs_covered(self):
        for i, a in enumerate(RARITY_ORDER):
            for b in RARITY_ORDER[i:]:
                assert (a, b) in _RARITY_WEIGHTS, f"Missing weight entry for ({a}, {b})"

    def test_weights_sum_to_100(self):
        for pair, weights in _RARITY_WEIGHTS.items():
            total = sum(weights)
            assert abs(total - 100) < 1, f"{pair} weights sum to {total}, expected ~100"

    def test_legendary_possible_from_any_pair(self):
        for pair, weights in _RARITY_WEIGHTS.items():
            assert weights[3] > 0, f"{pair} has 0% legendary chance"

    def test_common_possible_from_any_pair(self):
        for pair, weights in _RARITY_WEIGHTS.items():
            assert weights[0] > 0, f"{pair} has 0% common chance"

    def test_low_tier_pairs_heavily_favour_lower_rarities(self):
        thresholds = {
            ("common", "common"): 2,
            ("common", "rare"): 7,
            ("rare", "rare"): 11,
        }
        for pair, max_pct in thresholds.items():
            high_rarity_pct = _RARITY_WEIGHTS[pair][2] + _RARITY_WEIGHTS[pair][3]
            assert high_rarity_pct <= max_pct, f"{pair} has {high_rarity_pct}% epic+legendary"

    def test_higher_rarity_parents_shift_distribution_upward(self):
        assert (
            _RARITY_WEIGHTS[("legendary", "legendary")][3]
            > _RARITY_WEIGHTS[("common", "common")][3]
        )

    def test_resolve_offspring_symmetric(self, conn):
        import random

        random.seed(42)
        id_ab = resolve_offspring("rare", "epic", _candidates(conn))
        random.seed(42)
        id_ba = resolve_offspring("epic", "rare", _candidates(conn))
        assert id_ab == id_ba
