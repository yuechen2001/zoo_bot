import math
import pytest
from game.mood_engine import get_streak_multiplier, calc_coins, streak_label


class TestGetStreakMultiplier:
    def test_zero(self):
        assert get_streak_multiplier(0) == 1.0

    def test_below_4(self):
        assert get_streak_multiplier(3) == 1.0

    def test_at_4(self):
        assert get_streak_multiplier(4) == 1.25

    def test_at_7(self):
        assert get_streak_multiplier(7) == 1.25

    def test_at_8(self):
        assert get_streak_multiplier(8) == 1.5

    def test_at_15(self):
        assert get_streak_multiplier(15) == 1.5

    def test_at_16(self):
        assert get_streak_multiplier(16) == 2.0

    def test_at_29(self):
        assert get_streak_multiplier(29) == 2.0

    def test_at_30(self):
        assert get_streak_multiplier(30) == 3.0

    def test_above_30(self):
        assert get_streak_multiplier(50) == 3.0


class TestCalcCoins:
    def test_sad_no_streak(self):
        assert calc_coins("😢", 0) == 10

    def test_neutral_no_streak(self):
        assert calc_coins("😐", 0) == 20

    def test_pretty_good_no_streak(self):
        assert calc_coins("🙂", 0) == 35

    def test_great_no_streak(self):
        assert calc_coins("😄", 0) == 55

    def test_amazing_no_streak(self):
        assert calc_coins("🤩", 0) == 80

    def test_floor_rounding(self):
        # 🙂 base=35, multiplier at streak=4 is 1.25 → 35 * 1.25 = 43.75 → floor → 43
        assert calc_coins("🙂", 4) == 43

    def test_amazing_max_streak(self):
        # 80 * 3.0 = 240
        assert calc_coins("🤩", 30) == 240

    def test_great_mid_streak(self):
        # 55 * 1.5 = 82.5 → floor → 82
        assert calc_coins("😄", 8) == math.floor(55 * 1.5)

    def test_unknown_emoji_defaults_to_20(self):
        assert calc_coins("❓", 0) == 20

    def test_streak_multiplier_applied(self):
        no_streak = calc_coins("😄", 0)
        with_streak = calc_coins("😄", 16)
        assert with_streak == math.floor(55 * 2.0)
        assert with_streak > no_streak


class TestStreakLabel:
    def test_zero_windows(self):
        assert streak_label(0) == "No streak yet"

    def test_one_window_singular(self):
        label = streak_label(1)
        assert "1 window" in label
        assert "windows" not in label
        assert "(1.0x)" in label

    def test_plural_windows(self):
        label = streak_label(3)
        assert "3 windows" in label
        assert "(1.0x)" in label

    def test_at_4_shows_125(self):
        assert "(1.25x)" in streak_label(4)

    def test_at_8_shows_15(self):
        assert "(1.5x)" in streak_label(8)

    def test_at_16_shows_2(self):
        assert "(2.0x)" in streak_label(16)

    def test_at_30_shows_3_and_fire(self):
        label = streak_label(30)
        assert "(3.0x" in label
        assert "🔥" in label

    def test_at_29_still_2x(self):
        assert "(2.0x)" in streak_label(29)
