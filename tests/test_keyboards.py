from keyboards import (
    mood_keyboard,
    catch_keyboard,
    breed_collect_keyboard,
    MOOD_EMOJIS,
    zoo_page_keyboard,
    directory_page_keyboard,
    store_tab_keyboard,
    lure_keyboard,
    trade_keyboard,
)


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


_HABITATS_3 = ["woodland", "aquatic", "savanna"]


class TestZooPageKeyboard:
    def test_first_page_no_prev_has_next(self):
        kb = zoo_page_keyboard(1, 0, _HABITATS_3)
        texts = [btn.callback_data for btn in kb.inline_keyboard[0]]
        assert not any(t.endswith("_-1") or "zoo_page" not in t and "◀" in t for t in texts)
        assert any("zoo_page_1_1" == t for t in texts)
        assert not any(f"zoo_page_1_{-1}" in t for t in texts)

    def test_first_page_has_no_prev_button(self):
        kb = zoo_page_keyboard(1, 0, _HABITATS_3)
        callbacks = [btn.callback_data for btn in kb.inline_keyboard[0]]
        assert "zoo_page_1_-1" not in callbacks
        assert not any(cb == "zoo_page_1_-1" for cb in callbacks)
        assert all("_-1" not in cb for cb in callbacks)

    def test_first_page_has_next_button(self):
        kb = zoo_page_keyboard(1, 0, _HABITATS_3)
        callbacks = [btn.callback_data for btn in kb.inline_keyboard[0]]
        assert "zoo_page_1_1" in callbacks

    def test_last_page_has_prev_no_next(self):
        kb = zoo_page_keyboard(1, 2, _HABITATS_3)
        callbacks = [btn.callback_data for btn in kb.inline_keyboard[0]]
        assert "zoo_page_1_1" in callbacks
        assert "zoo_page_1_3" not in callbacks

    def test_middle_page_has_both(self):
        kb = zoo_page_keyboard(1, 1, _HABITATS_3)
        callbacks = [btn.callback_data for btn in kb.inline_keyboard[0]]
        assert "zoo_page_1_0" in callbacks
        assert "zoo_page_1_2" in callbacks


class TestDirectoryPageKeyboard:
    def test_first_page_has_next_no_prev(self):
        kb = directory_page_keyboard(1, 0, _HABITATS_3)
        callbacks = [btn.callback_data for btn in kb.inline_keyboard[0]]
        assert "dir_page_1_1" in callbacks
        assert all("_-1" not in cb for cb in callbacks)

    def test_last_page_has_prev_no_next(self):
        kb = directory_page_keyboard(1, 2, _HABITATS_3)
        callbacks = [btn.callback_data for btn in kb.inline_keyboard[0]]
        assert "dir_page_1_1" in callbacks
        assert "dir_page_1_3" not in callbacks

    def test_middle_page_has_both(self):
        kb = directory_page_keyboard(1, 1, _HABITATS_3)
        callbacks = [btn.callback_data for btn in kb.inline_keyboard[0]]
        assert "dir_page_1_0" in callbacks
        assert "dir_page_1_2" in callbacks


class TestStoreTabKeyboard:
    def test_unowned_cosmetic_shows_price_button(self):
        kb = store_tab_keyboard("titles", owned_keys=set(), counts={})
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert any(cb.startswith("store_buy_") for cb in all_callbacks)

    def test_owned_cosmetic_shows_noop_button(self):
        from game.store_data import COSMETICS

        first_key = next(iter(COSMETICS))
        kb = store_tab_keyboard("titles", owned_keys={first_key}, counts={})
        all_btns = [btn for row in kb.inline_keyboard for btn in row]
        noop_btn = next(b for b in all_btns if b.callback_data == "zoo_noop" and "✅" in b.text)
        assert noop_btn is not None

    def test_active_tab_shows_marker(self):
        kb = store_tab_keyboard("items", owned_keys=set(), counts={})
        tab_row = kb.inline_keyboard[0]
        active_btn = next(b for b in tab_row if b.callback_data == "zoo_noop")
        assert "▸" in active_btn.text


class TestLureKeyboard:
    def test_single_count_no_multiplier(self):
        kb = lure_keyboard({"lure_woodland": 1})
        all_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        lure_btns = [t for t in all_texts if "Cancel" not in t]
        assert all("×" not in t for t in lure_btns)

    def test_count_three_shows_multiplier(self):
        kb = lure_keyboard({"lure_woodland": 3})
        all_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        lure_btns = [t for t in all_texts if "Cancel" not in t]
        assert any("×3" in t for t in lure_btns)

    def test_empty_shows_no_lure_and_cancel(self):
        kb = lure_keyboard({})
        all_rows = kb.inline_keyboard
        assert len(all_rows) == 2
        assert all_rows[0][0].callback_data == "catch_lure_none"
        assert all_rows[1][0].callback_data == "catch_cancel"


class TestStoreTabKeyboardLures:
    def test_lures_tab_has_store_buy_callbacks(self):
        kb = store_tab_keyboard("lures", owned_keys=set(), counts={})
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert any(cb.startswith("store_buy_lure_") for cb in all_callbacks)


class TestTradeKeyboard:
    def test_accept_button_callback(self):
        kb = trade_keyboard(42, 7)
        btns = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [b.callback_data for b in btns]
        assert "trade_accept_42_7" in callbacks

    def test_decline_button_callback(self):
        kb = trade_keyboard(42, 7)
        btns = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [b.callback_data for b in btns]
        assert "trade_decline_42_7" in callbacks
