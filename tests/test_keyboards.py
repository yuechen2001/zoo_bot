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
    def test_active_habitat_is_noop(self):
        kb = zoo_page_keyboard(1, 0, _HABITATS_3)
        all_btns = [btn for row in kb.inline_keyboard for btn in row]
        assert all_btns[0].callback_data == "zoo_noop"
        assert "▸" in all_btns[0].text

    def test_inactive_habitats_have_callbacks(self):
        kb = zoo_page_keyboard(1, 0, _HABITATS_3)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "zoo_page_1_1" in all_callbacks
        assert "zoo_page_1_2" in all_callbacks

    def test_no_out_of_range_callback(self):
        kb = zoo_page_keyboard(1, 0, _HABITATS_3)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert all("_-1" not in cb for cb in all_callbacks)
        assert "zoo_page_1_3" not in all_callbacks

    def test_buttons_in_rows_of_three(self):
        kb = zoo_page_keyboard(1, 0, _HABITATS_3)
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 3

    def test_five_habitats_wraps_to_two_rows(self):
        five = ["woodland", "savanna", "tropical", "aquatic", "tundra"]
        kb = zoo_page_keyboard(1, 0, five)
        assert len(kb.inline_keyboard) == 2
        assert len(kb.inline_keyboard[0]) == 3
        assert len(kb.inline_keyboard[1]) == 2

    def test_middle_page_active_others_clickable(self):
        kb = zoo_page_keyboard(1, 1, _HABITATS_3)
        all_btns = [btn for row in kb.inline_keyboard for btn in row]
        assert all_btns[1].callback_data == "zoo_noop"
        assert all_btns[0].callback_data == "zoo_page_1_0"
        assert all_btns[2].callback_data == "zoo_page_1_2"


class TestDirectoryPageKeyboard:
    def test_active_habitat_is_noop(self):
        kb = directory_page_keyboard(1, 0, _HABITATS_3)
        all_btns = [btn for row in kb.inline_keyboard for btn in row]
        assert all_btns[0].callback_data == "zoo_noop"
        assert "▸" in all_btns[0].text

    def test_inactive_habitats_have_callbacks(self):
        kb = directory_page_keyboard(1, 0, _HABITATS_3)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "dir_page_1_1" in all_callbacks
        assert "dir_page_1_2" in all_callbacks

    def test_no_out_of_range_callback(self):
        kb = directory_page_keyboard(1, 2, _HABITATS_3)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert all("_-1" not in cb for cb in all_callbacks)
        assert "dir_page_1_3" not in all_callbacks

    def test_middle_page_active_others_clickable(self):
        kb = directory_page_keyboard(1, 1, _HABITATS_3)
        all_btns = [btn for row in kb.inline_keyboard for btn in row]
        assert all_btns[1].callback_data == "zoo_noop"
        assert all_btns[0].callback_data == "dir_page_1_0"
        assert all_btns[2].callback_data == "dir_page_1_2"


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

    def test_always_has_no_lure_option(self):
        kb = lure_keyboard({"lure_woodland": 2})
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "catch_lure_none" in all_callbacks


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
