import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.achievements import achievements_command
from game.achievements import check_achievements, ACHIEVEMENTS
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_user(**kwargs):
    defaults = {"user_id": 1, "username": "tester", "group_chat_id": None, "coins": 100}
    defaults.update(kwargs)
    return make_row(**defaults)


@pytest.mark.asyncio
async def test_achievements_unregistered_user():
    update = _make_update()
    with patch("handlers.achievements.db.get_user", return_value=None):
        await achievements_command(update, MagicMock(user_data={}))
    reply = update.message.reply_text.call_args[0][0]
    assert "start" in reply.lower()


@pytest.mark.asyncio
async def test_achievements_none_earned():
    update = _make_update()
    with patch("handlers.achievements.db.get_user", return_value=_make_user()), patch(
        "handlers.achievements.db.get_achievement_keys", return_value=set()
    ):
        await achievements_command(update, MagicMock(user_data={}))
    reply = update.message.reply_text.call_args[0][0]
    assert "0/" in reply
    assert "None yet" in reply


@pytest.mark.asyncio
async def test_achievements_some_earned():
    update = _make_update()
    from game.achievements import ACHIEVEMENTS

    first_key = next(iter(ACHIEVEMENTS))
    with patch("handlers.achievements.db.get_user", return_value=_make_user()), patch(
        "handlers.achievements.db.get_achievement_keys", return_value={first_key}
    ):
        await achievements_command(update, MagicMock(user_data={}))
    reply = update.message.reply_text.call_args[0][0]
    assert "1/" in reply


@pytest.mark.asyncio
async def test_achievements_shows_locked_entries():
    update = _make_update()
    with patch("handlers.achievements.db.get_user", return_value=_make_user()), patch(
        "handlers.achievements.db.get_achievement_keys", return_value=set()
    ):
        await achievements_command(update, MagicMock(user_data={}))
    reply = update.message.reply_text.call_args[0][0]
    assert "🔒" in reply


@pytest.mark.asyncio
async def test_check_achievements_uses_row_key_access():
    """Regression: check_achievements must not call .get() on the sqlite3.Row user object."""
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    user = _make_user(username="tester", group_chat_id=-100)

    with patch("game.achievements.db.get_user", return_value=user), patch(
        "game.achievements.db.get_achievement_keys", return_value=set()
    ), patch("game.achievements.db.award_achievement"), patch(
        "game.achievements.ACHIEVEMENTS",
        {
            "test_ach": {
                "trigger": "checkin",
                "check": lambda uid, u: True,
                "name": "Test",
                "emoji": "🏆",
                "desc": "Test achievement",
            }
        },
    ):
        # This would raise AttributeError if user.get() is called on a FakeRow
        await check_achievements(1, "checkin", ctx)

    ctx.bot.send_message.assert_called_once()


# ── New achievement check function tests ──────────────────────────────────────


def _get_check(key):
    return ACHIEVEMENTS[key]["check"]


def test_zoo_30_check():
    check = _get_check("zoo_30")
    with patch("game.achievements.db.count_animals", return_value=30):
        assert check(1, {}) is True
    with patch("game.achievements.db.count_animals", return_value=29):
        assert check(1, {}) is False


def test_species_20_check():
    check = _get_check("species_20")
    with patch("game.achievements.db.count_distinct_species", return_value=20):
        assert check(1, {}) is True
    with patch("game.achievements.db.count_distinct_species", return_value=19):
        assert check(1, {}) is False


def test_mythic_tamer_check():
    check = _get_check("mythic_tamer")
    with patch("game.achievements.db.get_animal_count_by_habitat", return_value=1):
        assert check(1, {}) is True
    with patch("game.achievements.db.get_animal_count_by_habitat", return_value=0):
        assert check(1, {}) is False


def test_explorer_check_all_habitats():
    check = _get_check("explorer")
    with patch("game.achievements.db.get_animal_count_by_habitat", return_value=1):
        assert check(1, {}) is True


def test_explorer_check_missing_one_habitat():
    check = _get_check("explorer")

    # Return 0 only for "mythic", non-zero for others
    def side_effect(uid, h):
        return 0 if h == "mythic" else 1

    with patch("game.achievements.db.get_animal_count_by_habitat", side_effect=side_effect):
        assert check(1, {}) is False


def test_streak_100_check():
    check = _get_check("streak_100")
    assert check(1, {"streak_windows": 100}) is True
    assert check(1, {"streak_windows": 99}) is False
    assert check(1, {"streak_windows": None}) is False


def test_checkin_100_check():
    check = _get_check("checkin_100")
    with patch("game.achievements.db.count_mood_checkins", return_value=100):
        assert check(1, {}) is True
    with patch("game.achievements.db.count_mood_checkins", return_value=99):
        assert check(1, {}) is False


def test_coins_10000_check():
    check = _get_check("coins_10000")
    assert check(1, {"coins": 10000}) is True
    assert check(1, {"coins": 9999}) is False
    assert check(1, {"coins": None}) is False


def test_breed_20_check():
    check = _get_check("breed_20")
    with patch("game.achievements.db.count_collected_breeds", return_value=20):
        assert check(1, {}) is True
    with patch("game.achievements.db.count_collected_breeds", return_value=19):
        assert check(1, {}) is False


def test_explorer_requires_desert():
    check = _get_check("explorer")

    def missing_desert(uid, h):
        return 0 if h == "desert" else 1

    with patch("game.achievements.db.get_animal_count_by_habitat", side_effect=missing_desert):
        assert check(1, {}) is False


def test_desert_first_check():
    check = _get_check("desert_first")
    with patch("game.achievements.db.get_animal_count_by_habitat", return_value=1):
        assert check(1, {}) is True
    with patch("game.achievements.db.get_animal_count_by_habitat", return_value=0):
        assert check(1, {}) is False


def test_desert_collector_check():
    check = _get_check("desert_collector")
    with patch("game.achievements.db.get_animal_count_by_habitat", return_value=3):
        assert check(1, {}) is True
    with patch("game.achievements.db.get_animal_count_by_habitat", return_value=2):
        assert check(1, {}) is False


def test_desert_master_check():
    check = _get_check("desert_master")
    with patch("game.achievements.db.count_distinct_species_in_habitat", return_value=8):
        assert check(1, {}) is True
    with patch("game.achievements.db.count_distinct_species_in_habitat", return_value=7):
        assert check(1, {}) is False


def test_zoo_50_check():
    check = _get_check("zoo_50")
    with patch("game.achievements.db.count_animals", return_value=50):
        assert check(1, {}) is True
    with patch("game.achievements.db.count_animals", return_value=49):
        assert check(1, {}) is False


def test_species_30_check():
    check = _get_check("species_30")
    with patch("game.achievements.db.count_distinct_species", return_value=30):
        assert check(1, {}) is True
    with patch("game.achievements.db.count_distinct_species", return_value=29):
        assert check(1, {}) is False


def test_enclosure_level_6_check():
    check = _get_check("enclosure_level_6")
    with patch("game.achievements.db.get_max_enclosure_level", return_value=6):
        assert check(1, {}) is True
    with patch("game.achievements.db.get_max_enclosure_level", return_value=5):
        assert check(1, {}) is False


def test_enclosure_level_7_check():
    check = _get_check("enclosure_level_7")
    with patch("game.achievements.db.get_max_enclosure_level", return_value=7):
        assert check(1, {}) is True
    with patch("game.achievements.db.get_max_enclosure_level", return_value=6):
        assert check(1, {}) is False
    with patch("game.achievements.db.get_max_enclosure_level", return_value=5):
        assert check(1, {}) is False


# ── Achievement schema validation ─────────────────────────────────────────────


class TestAchievementSchema:
    def test_all_have_required_keys(self):
        required = {"emoji", "name", "desc", "trigger", "check"}
        for key, ach in ACHIEVEMENTS.items():
            missing = required - ach.keys()
            assert not missing, f"Achievement '{key}' missing fields: {missing}"

    def test_no_duplicate_names(self):
        names = [ach["name"] for ach in ACHIEVEMENTS.values()]
        assert len(names) == len(set(names)), "Duplicate achievement names found"

    def test_all_triggers_are_known(self):
        known = {
            "checkin",
            "catch",
            "breed",
            "trade",
            "sell",
            "feed",
            "trivia",
            "daily",
            "wild_catch",
            "store",
            "gift",
            "enclosure",
        }
        for key, ach in ACHIEVEMENTS.items():
            assert (
                ach["trigger"] in known
            ), f"Achievement '{key}' has unknown trigger '{ach['trigger']}'"


# ── check_achievements edge cases ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_achievements_skips_already_earned():
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    user = _make_user(username="tester", group_chat_id=-100)

    with patch("game.achievements.db.get_user", return_value=user), patch(
        "game.achievements.db.get_achievement_keys", return_value={"test_ach"}
    ), patch("game.achievements.db.award_achievement") as mock_award, patch(
        "game.achievements.ACHIEVEMENTS",
        {
            "test_ach": {
                "trigger": "checkin",
                "check": lambda uid, u: True,
                "name": "Test",
                "emoji": "🏆",
                "desc": "Already earned",
            }
        },
    ):
        await check_achievements(1, "checkin", ctx)

    mock_award.assert_not_called()
    ctx.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_achievements_skips_wrong_trigger():
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    user = _make_user(username="tester", group_chat_id=None)

    with patch("game.achievements.db.get_user", return_value=user), patch(
        "game.achievements.db.get_achievement_keys", return_value=set()
    ), patch("game.achievements.db.award_achievement") as mock_award, patch(
        "game.achievements.ACHIEVEMENTS",
        {
            "catch_ach": {
                "trigger": "catch",
                "check": lambda uid, u: True,
                "name": "Catcher",
                "emoji": "🎯",
                "desc": "Caught something",
            }
        },
    ):
        await check_achievements(1, "checkin", ctx)  # fires "checkin", not "catch"

    mock_award.assert_not_called()


# ── achievements_tab_callback ─────────────────────────────────────────────────


def _make_tab_callback(from_user_id=1, owner_id=1, filter_type="earned"):
    query = MagicMock()
    query.from_user.id = from_user_id
    query.data = f"ach_tab_{owner_id}_{filter_type}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query, MagicMock()


@pytest.mark.asyncio
async def test_tab_callback_wrong_user_blocked():
    from handlers.achievements import achievements_tab_callback

    update, query, ctx = _make_tab_callback(from_user_id=999, owner_id=1)
    await achievements_tab_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_tab_callback_earned_filter():
    from handlers.achievements import achievements_tab_callback

    update, query, ctx = _make_tab_callback(from_user_id=1, owner_id=1, filter_type="earned")
    first_key = next(iter(ACHIEVEMENTS))
    with patch("handlers.achievements.db.get_achievement_keys", return_value={first_key}):
        await achievements_tab_callback(update, ctx)
    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args[0][0]
    assert "1/" in text


@pytest.mark.asyncio
async def test_tab_callback_locked_filter():
    from handlers.achievements import achievements_tab_callback

    update, query, ctx = _make_tab_callback(from_user_id=1, owner_id=1, filter_type="locked")
    with patch("handlers.achievements.db.get_achievement_keys", return_value=set()):
        await achievements_tab_callback(update, ctx)
    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args[0][0]
    assert "🔒" in text


@pytest.mark.asyncio
async def test_tab_callback_all_filter():
    from handlers.achievements import achievements_tab_callback

    update, query, ctx = _make_tab_callback(from_user_id=1, owner_id=1, filter_type="all")
    with patch("handlers.achievements.db.get_achievement_keys", return_value=set()):
        await achievements_tab_callback(update, ctx)
    query.edit_message_text.assert_called_once()


# ── check_achievements send path ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_achievements_sends_when_newly_earned():
    from game.achievements import check_achievements

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    user = _make_user(username="zoe", group_chat_id=-200)

    with patch("game.achievements.db.get_user", return_value=user), patch(
        "game.achievements.db.get_achievement_keys", return_value=set()
    ), patch("game.achievements.db.award_achievement"), patch(
        "game.achievements.ACHIEVEMENTS",
        {
            "new_ach": {
                "trigger": "sell",
                "check": lambda uid, u: True,
                "name": "Seller",
                "emoji": "💸",
                "desc": "Sold something",
            }
        },
    ):
        await check_achievements(1, "sell", ctx)

    ctx.bot.send_message.assert_called_once()
    msg = ctx.bot.send_message.call_args[0][1]
    assert "Seller" in msg


@pytest.mark.asyncio
async def test_check_achievements_no_group_no_send():
    from game.achievements import check_achievements

    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    user = _make_user(username="solo", group_chat_id=None)

    with patch("game.achievements.db.get_user", return_value=user), patch(
        "game.achievements.db.get_achievement_keys", return_value=set()
    ), patch("game.achievements.db.award_achievement"), patch(
        "game.achievements.ACHIEVEMENTS",
        {
            "solo_ach": {
                "trigger": "catch",
                "check": lambda uid, u: True,
                "name": "Catcher",
                "emoji": "🎣",
                "desc": "Caught something",
            }
        },
    ):
        await check_achievements(1, "catch", ctx)

    ctx.bot.send_message.assert_not_called()
