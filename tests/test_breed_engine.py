import datetime
from unittest.mock import patch
from game.breed_engine import calc_breed_cost, breed_duration_str, calc_breed_ready_at, resolve_offspring


class TestCalcBreedCost:
    def test_common_common(self):
        assert calc_breed_cost("common", "common") == 50

    def test_common_rare(self):
        assert calc_breed_cost("common", "rare") == 120

    def test_rare_rare(self):
        assert calc_breed_cost("rare", "rare") == 200

    def test_common_epic(self):
        assert calc_breed_cost("common", "epic") == 350

    def test_rare_epic(self):
        assert calc_breed_cost("rare", "epic") == 350

    def test_epic_epic(self):
        assert calc_breed_cost("epic", "epic") == 500

    def test_common_legendary(self):
        assert calc_breed_cost("common", "legendary") == 800

    def test_rare_legendary(self):
        assert calc_breed_cost("rare", "legendary") == 800

    def test_epic_legendary(self):
        assert calc_breed_cost("epic", "legendary") == 800

    def test_legendary_legendary(self):
        assert calc_breed_cost("legendary", "legendary") == 800

    def test_symmetry_common_rare(self):
        assert calc_breed_cost("rare", "common") == calc_breed_cost("common", "rare")

    def test_symmetry_epic_legendary(self):
        assert calc_breed_cost("legendary", "epic") == calc_breed_cost("epic", "legendary")


class TestBreedDurationStr:
    def test_common_common_6h(self):
        assert breed_duration_str("common", "common") == "6h"

    def test_rare_rare_18h(self):
        assert breed_duration_str("rare", "rare") == "18h"

    def test_common_legendary_48h_is_2d(self):
        assert breed_duration_str("common", "legendary") == "2d"

    def test_legendary_legendary_48h_is_2d(self):
        assert breed_duration_str("legendary", "legendary") == "2d"

    def test_common_epic_28h_is_1d4h(self):
        assert breed_duration_str("common", "epic") == "1d 4h"

    def test_epic_epic_36h_is_1d12h(self):
        assert breed_duration_str("epic", "epic") == "1d 12h"


class TestCalcBreedReadyAt:
    def test_returns_future_timestamp(self):
        before = datetime.datetime.utcnow()
        ts = calc_breed_ready_at("common", "common")
        dt = datetime.datetime.fromisoformat(ts)
        assert dt > before

    def test_common_common_approx_6h(self):
        ts = calc_breed_ready_at("common", "common")
        dt = datetime.datetime.fromisoformat(ts)
        delta = dt - datetime.datetime.utcnow()
        assert abs(delta.total_seconds() - 6 * 3600) < 5

    def test_legendary_legendary_approx_48h(self):
        ts = calc_breed_ready_at("legendary", "legendary")
        dt = datetime.datetime.fromisoformat(ts)
        delta = dt - datetime.datetime.utcnow()
        assert abs(delta.total_seconds() - 48 * 3600) < 5


class TestResolveOffspring:
    def test_no_bump_picks_higher_rarity(self, conn):
        # random[0]=0.5 → no bump (>0.10); random[1]=0.3 → picks higher (< 0.7)
        with patch("game.breed_engine.random.random", side_effect=[0.5, 0.3]):
            species_id = resolve_offspring("common", "rare", conn)
        row = conn.execute("SELECT rarity FROM species WHERE species_id=?", (species_id,)).fetchone()
        assert row["rarity"] == "rare"

    def test_no_bump_picks_lower_rarity(self, conn):
        # random[0]=0.5 → no bump; random[1]=0.9 → picks lower (>= 0.7)
        with patch("game.breed_engine.random.random", side_effect=[0.5, 0.9]):
            species_id = resolve_offspring("common", "rare", conn)
        row = conn.execute("SELECT rarity FROM species WHERE species_id=?", (species_id,)).fetchone()
        assert row["rarity"] == "common"

    def test_bump_on_common_common_gives_rare(self, conn):
        # random[0]=0.05 → bump (< 0.10); common → rare
        with patch("game.breed_engine.random.random", return_value=0.05):
            species_id = resolve_offspring("common", "common", conn)
        row = conn.execute("SELECT rarity FROM species WHERE species_id=?", (species_id,)).fetchone()
        assert row["rarity"] == "rare"

    def test_legendary_cannot_bump_further(self, conn):
        # Even with bump roll, legendary is capped (higher_idx == 3 == len-1)
        # Falls to else branch: random[1]=0.3 → picks higher = legendary
        with patch("game.breed_engine.random.random", side_effect=[0.05, 0.3]):
            species_id = resolve_offspring("legendary", "legendary", conn)
        row = conn.execute("SELECT rarity FROM species WHERE species_id=?", (species_id,)).fetchone()
        assert row["rarity"] == "legendary"

    def test_returns_valid_species_id(self, conn):
        species_id = resolve_offspring("common", "common", conn)
        row = conn.execute("SELECT species_id FROM species WHERE species_id=?", (species_id,)).fetchone()
        assert row is not None
