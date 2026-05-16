import pytest
from keyboards import mood_keyboard, catch_keyboard, breed_collect_keyboard, MOOD_EMOJIS


class TestMoodKeyboard:
    def test_callback_data_includes_user_id(self):
        kb = mood_keyboard(12345)
        for btn in kb.inline_keyboard[0]:
            assert btn.callback_data.startswith("mood_12345_"), (
                f"Expected mood_12345_<emoji>, got {btn.callback_data}"
            )

    def test_all_mood_emojis_present(self):
        kb = mood_keyboard(99)
        emojis = [btn.callback_data.split("_", 2)[2] for btn in kb.inline_keyboard[0]]
        assert emojis == MOOD_EMOJIS

    def test_different_user_ids_produce_different_callbacks(self):
        data1 = [btn.callback_data for btn in mood_keyboard(111).inline_keyboard[0]]
        data2 = [btn.callback_data for btn in mood_keyboard(222).inline_keyboard[0]]
        assert data1 != data2

    def test_format_is_mood_userid_emoji(self):
        kb = mood_keyboard(42)
        for btn in kb.inline_keyboard[0]:
            parts = btn.callback_data.split("_", 2)
            assert len(parts) == 3
            assert parts[0] == "mood"
            assert parts[1] == "42"
            assert parts[2] in MOOD_EMOJIS


class TestCatchKeyboard:
    def test_attempt_button_callback_data(self):
        kb = catch_keyboard(7, 150)
        attempt_btn = kb.inline_keyboard[0][0]
        assert attempt_btn.callback_data == "catch_attempt_7"

    def test_attempt_button_shows_cost(self):
        kb = catch_keyboard(7, 150)
        attempt_btn = kb.inline_keyboard[0][0]
        assert "150" in attempt_btn.text

    def test_skip_button_callback_data(self):
        kb = catch_keyboard(7, 150)
        skip_btn = kb.inline_keyboard[0][1]
        assert skip_btn.callback_data == "catch_skip"


class TestBreedCollectKeyboard:
    def test_has_collect_button(self):
        kb = breed_collect_keyboard()
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "breed_collect"
