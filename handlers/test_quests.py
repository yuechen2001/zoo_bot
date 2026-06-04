import pytest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from handlers.quests import quests_command, quest_tab_callback, _render_quests
from game.quests_data import CHAPTERS, ARCS, check_quest_advance
from game.constants import QUEST_CHAPTER_COUNT


# ── Constants ──────────────────────────────────────────────────────────────────


def test_quest_chapter_count():
    assert QUEST_CHAPTER_COUNT == 21


def test_chapters_dict_has_21_entries():
    assert len(CHAPTERS) == 21


def test_arcs_dict_has_7_entries():
    assert len(ARCS) == 7


def test_every_chapter_has_required_fields():
    required = {"arc", "title", "intro", "outro", "tasks", "reward_coins"}
    for num, ch in CHAPTERS.items():
        for field in required:
            assert field in ch, f"Chapter {num} missing field '{field}'"


def test_every_chapter_has_at_least_one_task():
    for num, ch in CHAPTERS.items():
        assert len(ch["tasks"]) >= 1, f"Chapter {num} has no tasks"
        for task in ch["tasks"]:
            assert "desc" in task and "check" in task


def test_arc_numbers_are_valid():
    for num, ch in CHAPTERS.items():
        assert ch["arc"] in ARCS, f"Chapter {num} has unknown arc {ch['arc']}"


def test_reward_species_are_none_or_string():
    for num, ch in CHAPTERS.items():
        assert ch.get("reward_species") is None or isinstance(
            ch["reward_species"], str
        ), f"Chapter {num} reward_species must be None or str"


def test_species_rewards_are_on_arc_endings():
    species_rewards = {
        num: ch["reward_species"] for num, ch in CHAPTERS.items() if ch["reward_species"]
    }
    assert set(species_rewards.keys()) == {3, 6, 9, 12, 15, 18, 21}


def test_chapter_12_has_title_reward():
    assert CHAPTERS[12]["reward_title"] == "title_expedition"


def test_chapter_21_has_title_reward():
    assert CHAPTERS[21]["reward_title"] == "title_eternal"


def test_reward_coins_increase_over_arcs():
    arc_coins = {}
    for ch in CHAPTERS.values():
        arc_coins.setdefault(ch["arc"], []).append(ch["reward_coins"])
    arc_averages = {arc: sum(coins) / len(coins) for arc, coins in arc_coins.items()}
    for arc in range(1, 7):
        assert (
            arc_averages[arc] < arc_averages[arc + 1]
        ), f"Arc {arc} avg coins not less than Arc {arc + 1}"


# ── check_quest_advance ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_quest_advance_no_op_for_missing_user():
    ctx = MagicMock()
    with patch("game.quests_data.db.get_user", return_value=None):
        await check_quest_advance(1, ctx)


@pytest.mark.asyncio
async def test_check_quest_advance_starts_chapter_1_on_first_call():
    ctx = MagicMock()
    user = {"group_chat_id": None, "streak_windows": 5, "feeds_given": 2, "coins": 100}
    with (
        patch("game.quests_data.db.get_user", return_value=user),
        patch("game.quests_data.db.get_quest_progress", return_value=[]),
        patch("game.quests_data.db.start_chapter") as mock_start,
        patch("game.quests_data.db.get_active_chapter", return_value=None),
    ):
        await check_quest_advance(1, ctx)
        mock_start.assert_called_once_with(1, 1)


@pytest.mark.asyncio
async def test_check_quest_advance_completes_chapter_when_all_tasks_pass():
    ctx = MagicMock()
    ctx.bot = MagicMock()
    ctx.bot.send_message = AsyncMock()
    user = {
        "group_chat_id": 100,
        "username": "tester",
        "streak_windows": 5,
        "feeds_given": 1,
        "coins": 200,
    }

    chapter_1_row = MagicMock()
    chapter_1_row.__getitem__ = lambda self, key: {
        "chapter_num": 1,
        "step": 3,
        "completed_at": "2024-01-01",
    }[key]

    with (
        patch("game.quests_data.db.get_user", return_value=user),
        patch("game.quests_data.db.get_quest_progress", return_value=[chapter_1_row]),
        patch("game.quests_data.db.get_active_chapter", return_value=None),
    ):
        await check_quest_advance(1, ctx)
        ctx.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_quest_advance_silently_ignores_db_errors():
    ctx = MagicMock()
    with patch("game.quests_data.db.get_user", side_effect=Exception("db gone")):
        await check_quest_advance(1, ctx)


# ── /quests command ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quests_command_requires_start():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()

    with patch("handlers.quests.db.get_user", return_value=None):
        await quests_command(update, ctx)
    update.message.reply_text.assert_called_once_with("Use /start first!")


@pytest.mark.asyncio
async def test_quests_command_sends_arc_1_by_default():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    user = {"group_chat_id": None, "streak_windows": 0, "feeds_given": 0, "coins": 0}

    with (
        patch("handlers.quests.db.get_user", return_value=user),
        patch("handlers.quests.db.get_quest_progress", return_value=[]),
        patch("handlers.quests.check_quest_advance", new_callable=AsyncMock),
        patch("handlers.quests._render_quests", return_value="rendered"),
        patch("handlers.quests.quests_keyboard", return_value=MagicMock()),
    ):
        await quests_command(update, ctx)
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert call_args[0][0] == "rendered"


# ── quest_tab_callback ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quest_tab_callback_rejects_wrong_user():
    query = MagicMock()
    query.from_user.id = 99
    query.data = "quest_arc_1_2"
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()

    await quest_tab_callback(update, ctx)
    query.answer.assert_called_once_with("Use /quests to see your own.", show_alert=True)


@pytest.mark.asyncio
async def test_quest_tab_callback_renders_correct_arc():
    query = MagicMock()
    query.from_user.id = 1
    query.data = "quest_arc_1_3"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()

    with (
        patch("handlers.quests.check_quest_advance", new_callable=AsyncMock),
        patch("handlers.quests.db.get_quest_progress", return_value=[]),
        patch("handlers.quests._render_quests", return_value="arc3_render") as mock_render,
        patch("handlers.quests.quests_keyboard", return_value=MagicMock()),
    ):
        await quest_tab_callback(update, ctx)
    mock_render.assert_called_once_with(1, arc=3)
    query.edit_message_text.assert_called_once()


# ── _render_quests ─────────────────────────────────────────────────────────────


def _quest_db_patches(user):
    """Patch all db calls reachable from task check lambdas in game/quests_data.py."""
    return (
        patch("game.quests_data.db.get_user", return_value=user),
        patch("game.quests_data.db.count_animals", return_value=0),
        patch("game.quests_data.db.count_mood_checkins", return_value=0),
        patch("game.quests_data.db.user_owns_rarity", return_value=False),
        patch("game.quests_data.db.count_trivia_answered", return_value=0),
        patch("game.quests_data.db.get_max_enclosure_level", return_value=1),
        patch("game.quests_data.db.count_collected_breeds", return_value=0),
        patch("game.quests_data.db.has_any_lure", return_value=False),
        patch("game.quests_data.db.has_any_store_item", return_value=False),
        patch("game.quests_data.db.has_any_investment", return_value=False),
        patch("game.quests_data.db.count_habitats_occupied", return_value=0),
        patch("game.quests_data.db.count_distinct_species", return_value=0),
        patch("game.quests_data.db.user_bred_rarity", return_value=False),
    )


def test_render_quests_shows_active_chapter():
    user = {"group_chat_id": None, "streak_windows": 2, "feeds_given": 1, "coins": 100}
    with ExitStack() as stack:
        stack.enter_context(patch("handlers.quests.db.get_quest_progress", return_value=[]))
        stack.enter_context(patch("handlers.quests.db.get_active_chapter", return_value=1))
        stack.enter_context(patch("handlers.quests.db.get_user", return_value=user))
        stack.enter_context(patch("handlers.quests.db.get_species_by_name", return_value=None))
        for p in _quest_db_patches(user):
            stack.enter_context(p)
        text = _render_quests(1, arc=1)
    assert "▶️" in text
    assert "First Steps" in text


def test_render_quests_shows_locked_future_chapters():
    user = {"group_chat_id": None, "streak_windows": 0, "feeds_given": 0, "coins": 0}

    ch1_row = MagicMock()
    ch1_row.__getitem__ = lambda self, key: {
        "chapter_num": 1,
        "step": 3,
        "completed_at": "2024-01-01",
    }[key]

    with ExitStack() as stack:
        stack.enter_context(patch("handlers.quests.db.get_quest_progress", return_value=[ch1_row]))
        stack.enter_context(patch("handlers.quests.db.get_active_chapter", return_value=2))
        stack.enter_context(patch("handlers.quests.db.get_user", return_value=user))
        stack.enter_context(patch("handlers.quests.db.get_species_by_name", return_value=None))
        for p in _quest_db_patches(user):
            stack.enter_context(p)
        text = _render_quests(1, arc=1)
    assert "✅" in text
    assert "▶️" in text


def test_render_quests_shows_arc_name():
    user = {"group_chat_id": None, "streak_windows": 0, "feeds_given": 0, "coins": 0}
    with ExitStack() as stack:
        stack.enter_context(patch("handlers.quests.db.get_quest_progress", return_value=[]))
        stack.enter_context(patch("handlers.quests.db.get_active_chapter", return_value=1))
        stack.enter_context(patch("handlers.quests.db.get_user", return_value=user))
        stack.enter_context(patch("handlers.quests.db.get_species_by_name", return_value=None))
        for p in _quest_db_patches(user):
            stack.enter_context(p)
        text = _render_quests(1, arc=1)
    assert "The Zoo Opens" in text
