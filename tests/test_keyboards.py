from keyboards import mood_keyboard, catch_keyboard, breed_collect_keyboard, MOOD_EMOJIS


class TestMoodKeyboard:
    def test_all_mood_emojis_present(self):
        kb = mood_keyboard()
        emojis = [btn.text for btn in kb.inline_keyboard[0]]
        assert emojis == MOOD_EMOJIS

    def test_callback_data_starts_with_mood(self):
        kb = mood_keyboard()
        for btn in kb.inline_keyboard[0]:
            assert btn.callback_data.startswith("mood_")

    def test_callback_data_contains_emoji(self):
        kb = mood_keyboard()
        for btn in kb.inline_keyboard[0]:
            emoji = btn.callback_data[len("mood_") :]
            assert emoji in MOOD_EMOJIS

    def test_five_buttons(self):
        kb = mood_keyboard()
        assert len(kb.inline_keyboard[0]) == len(MOOD_EMOJIS)


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
