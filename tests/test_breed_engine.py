from game.breed_engine import resolve_offspring, _RARITY_WEIGHTS
from species_data import RARITY_ORDER


def _candidates(conn):
    return lambda r: conn.execute("SELECT * FROM species WHERE rarity = ?", (r,)).fetchall()


class TestResolveOffspring:
    def test_returns_valid_species_id(self, conn):
        species_id = resolve_offspring("common", "common", _candidates(conn))
        row = conn.execute("SELECT * FROM species WHERE species_id = ?", (species_id,)).fetchone()
        assert row is not None

    def test_all_rarity_pairs_covered(self):
        """Every sorted pair in RARITY_ORDER must have a weight entry."""
        for i, a in enumerate(RARITY_ORDER):
            for b in RARITY_ORDER[i:]:
                assert (a, b) in _RARITY_WEIGHTS, f"Missing weight entry for ({a}, {b})"

    def test_weights_sum_to_100(self):
        for pair, weights in _RARITY_WEIGHTS.items():
            total = sum(weights)
            assert abs(total - 100) < 1, f"{pair} weights sum to {total}, expected ~100"

    def test_legendary_possible_from_any_pair(self):
        """Every pair must have a non-zero legendary weight."""
        for pair, weights in _RARITY_WEIGHTS.items():
            assert weights[3] > 0, f"{pair} has 0% legendary chance"

    def test_common_possible_from_any_pair(self):
        """Every pair must have a non-zero common weight."""
        for pair, weights in _RARITY_WEIGHTS.items():
            assert weights[0] > 0, f"{pair} has 0% common chance"

    def test_low_tier_pairs_heavily_favour_lower_rarities(self):
        """Low-tier pairs should have most weight on common/rare, not epic/legendary."""
        thresholds = {
            ("common", "common"): 2,  # 1.5+0.5 = 2%
            ("common", "rare"): 7,  # 5+1 = 6%
            ("rare", "rare"): 11,  # 8+2 = 10%
        }
        for pair, max_pct in thresholds.items():
            weights = _RARITY_WEIGHTS[pair]
            high_rarity_pct = weights[2] + weights[3]  # epic + legendary
            assert (
                high_rarity_pct <= max_pct
            ), f"{pair} has {high_rarity_pct}% epic+legendary (expected ≤{max_pct}%)"

    def test_higher_rarity_parents_shift_distribution_upward(self):
        """legendary×legendary should have higher legendary weight than common×common."""
        ll_legendary = _RARITY_WEIGHTS[("legendary", "legendary")][3]
        cc_legendary = _RARITY_WEIGHTS[("common", "common")][3]
        assert ll_legendary > cc_legendary

    def test_resolve_offspring_symmetric(self, conn):
        """resolve_offspring(a, b) and resolve_offspring(b, a) use the same distribution."""
        import random

        random.seed(42)
        id_ab = resolve_offspring("rare", "epic", _candidates(conn))
        random.seed(42)
        id_ba = resolve_offspring("epic", "rare", _candidates(conn))
        assert id_ab == id_ba
