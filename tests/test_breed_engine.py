import datetime
from unittest.mock import patch
from game.breed_engine import (
    calc_breed_cost,
    breed_duration_str,
    calc_breed_ready_at,
    resolve_offspring,
)


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
        before = datetime.datetime.utcnow()
        ts = calc_breed_ready_at("common", "common")
        dt = datetime.datetime.fromisoformat(ts)
        assert dt > before

    def test_common_common_full_hunger_approx_30m(self):
        ts = calc_breed_ready_at("common", "common", 100, 100)
        dt = datetime.datetime.fromisoformat(ts)
        delta = dt - datetime.datetime.utcnow()
        assert abs(delta.total_seconds() - 30 * 60) < 5

    def test_legendary_legendary_full_hunger_approx_2h(self):
        ts = calc_breed_ready_at("legendary", "legendary", 100, 100)
        dt = datetime.datetime.fromisoformat(ts)
        delta = dt - datetime.datetime.utcnow()
        assert abs(delta.total_seconds() - 2 * 3600) < 5

    def test_low_hunger_makes_longer_breed(self):
        ts_full = calc_breed_ready_at("rare", "rare", 100, 100)
        ts_empty = calc_breed_ready_at("rare", "rare", 0, 0)
        dt_full = datetime.datetime.fromisoformat(ts_full)
        dt_empty = datetime.datetime.fromisoformat(ts_empty)
        assert dt_empty > dt_full


class TestResolveOffspring:
    def test_no_bump_picks_higher_rarity(self, conn):
        # random[0]=0.5 → no bump (>0.10); random[1]=0.3 → picks higher (< 0.7)
        with patch("game.breed_engine.random.random", side_effect=[0.5, 0.3]):
            species_id = resolve_offspring("common", "rare", conn)
        row = conn.execute(
            "SELECT rarity FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row["rarity"] == "rare"

    def test_no_bump_picks_lower_rarity(self, conn):
        # random[0]=0.5 → no bump; random[1]=0.9 → picks lower (>= 0.7)
        with patch("game.breed_engine.random.random", side_effect=[0.5, 0.9]):
            species_id = resolve_offspring("common", "rare", conn)
        row = conn.execute(
            "SELECT rarity FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row["rarity"] == "common"

    def test_bump_on_common_common_gives_rare(self, conn):
        # random[0]=0.05 → bump (< 0.10); common → rare
        with patch("game.breed_engine.random.random", return_value=0.05):
            species_id = resolve_offspring("common", "common", conn)
        row = conn.execute(
            "SELECT rarity FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row["rarity"] == "rare"

    def test_legendary_cannot_bump_further(self, conn):
        # Even with bump roll, legendary is capped (higher_idx == 3 == len-1)
        # Falls to else branch: random[1]=0.3 → picks higher = legendary
        with patch("game.breed_engine.random.random", side_effect=[0.05, 0.3]):
            species_id = resolve_offspring("legendary", "legendary", conn)
        row = conn.execute(
            "SELECT rarity FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row["rarity"] == "legendary"

    def test_returns_valid_species_id(self, conn):
        species_id = resolve_offspring("common", "common", conn)
        row = conn.execute(
            "SELECT species_id FROM species WHERE species_id=?", (species_id,)
        ).fetchone()
        assert row is not None
