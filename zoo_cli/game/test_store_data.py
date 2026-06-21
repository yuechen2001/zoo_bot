"""Tests for store_data filtering — special items must not appear in purchasable views."""

from game.store_data import COSMETICS, PURCHASABLE_COSMETICS, STORE_ITEMS

SPECIAL_TITLES = {"title_expedition", "title_eternal"}


def test_special_titles_have_is_special_flag():
    for key in SPECIAL_TITLES:
        assert STORE_ITEMS[key].get("is_special") is True, f"{key} missing is_special=True"


def test_special_titles_not_in_purchasable_cosmetics():
    for key in SPECIAL_TITLES:
        assert (
            key not in PURCHASABLE_COSMETICS
        ), f"{key} should be excluded from PURCHASABLE_COSMETICS"


def test_purchasable_cosmetics_all_have_nonzero_price():
    for key, item in PURCHASABLE_COSMETICS.items():
        assert item["price"] > 0, f"{key} has price=0 but is in PURCHASABLE_COSMETICS"


def test_special_titles_still_in_cosmetics():
    """COSMETICS includes special titles so inventory/zoo can display and equip them."""
    for key in SPECIAL_TITLES:
        assert key in COSMETICS, f"{key} should still be in COSMETICS for inventory/zoo use"


def test_purchasable_cosmetics_is_subset_of_cosmetics():
    assert set(PURCHASABLE_COSMETICS).issubset(set(COSMETICS))


def test_no_zero_price_purchasable_items():
    """No item in any purchasable view should have price=0."""
    from game.store_data import ITEMS, LURES

    for key, item in {**ITEMS, **LURES, **PURCHASABLE_COSMETICS}.items():
        assert item["price"] > 0, f"{key} has price=0 in a purchasable view"
