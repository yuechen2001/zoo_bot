"""Tests for the 1.5% shiny roll in catch_callback and wild_event_callback."""

import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.catch import catch_callback
from handlers.wild_event import wild_event_callback


def _make_pending(species_id=1):
    return {
        "species_id": species_id,
        "catch_rate": 0.9,
        "catch_cost": 20,
        "rarity": "common",
        "name": "Fox",
        "emoji": "🦊",
        "at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(),
        "message_id": 42,
        "lure_multiplier": 1.0,
        "enc_catch_bonus": 0.0,
    }


def _make_catch_context(pending):
    query = MagicMock()
    query.from_user.id = 1
    query.data = f"catch_attempt_{pending['species_id']}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.user_data = {"pending_catch": pending}
    return update, query, ctx


# ── catch shiny roll ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_catch_shiny_roll_sets_flag_when_under_threshold():
    pending = _make_pending()
    update, query, ctx = _make_catch_context(pending)

    with patch(
        "handlers.catch.db.get_user",
        return_value={"coins": 500, "lucky_catch_active": 0, "catch_net_active": 0},
    ), patch("handlers.catch.db.get_species_habitat", return_value="woodland"), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.catch.db.add_coins"
    ), patch(
        "handlers.catch.db.add_animal"
    ), patch(
        "handlers.catch.db.set_animal_shiny"
    ) as mock_shiny, patch(
        "handlers.catch.db.set_animal_stats"
    ), patch(
        "handlers.catch.roll_catch", return_value=True
    ), patch(
        "handlers.catch.random.random", return_value=0.010
    ), patch(  # 0.010 < 0.015 → shiny
        "handlers.catch.check_achievements", new_callable=AsyncMock
    ):
        await catch_callback(update, ctx)

    mock_shiny.assert_called_once()
    text = query.edit_message_text.call_args[0][0]
    assert "⭐" in text


@pytest.mark.asyncio
async def test_catch_shiny_roll_skips_flag_when_over_threshold():
    pending = _make_pending()
    update, query, ctx = _make_catch_context(pending)

    with patch(
        "handlers.catch.db.get_user",
        return_value={"coins": 500, "lucky_catch_active": 0, "catch_net_active": 0},
    ), patch("handlers.catch.db.get_species_habitat", return_value="woodland"), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.catch.db.add_coins"
    ), patch(
        "handlers.catch.db.add_animal"
    ), patch(
        "handlers.catch.db.set_animal_shiny"
    ) as mock_shiny, patch(
        "handlers.catch.db.set_animal_stats"
    ), patch(
        "handlers.catch.roll_catch", return_value=True
    ), patch(
        "handlers.catch.random.random", return_value=0.020
    ), patch(  # 0.020 >= 0.015 → not shiny
        "handlers.catch.check_achievements", new_callable=AsyncMock
    ):
        await catch_callback(update, ctx)

    mock_shiny.assert_not_called()
    text = query.edit_message_text.call_args[0][0]
    assert "⭐" not in text


@pytest.mark.asyncio
async def test_catch_shiny_not_called_on_miss():
    """Failed catch must never call set_animal_shiny."""
    pending = _make_pending()
    update, query, ctx = _make_catch_context(pending)

    with patch(
        "handlers.catch.db.get_user",
        return_value={"coins": 500, "lucky_catch_active": 0, "catch_net_active": 0},
    ), patch("handlers.catch.db.get_species_habitat", return_value="woodland"), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.catch.db.add_coins"
    ), patch(
        "handlers.catch.db.set_animal_shiny"
    ) as mock_shiny, patch(
        "handlers.catch.roll_catch", return_value=False
    ):
        await catch_callback(update, ctx)

    mock_shiny.assert_not_called()


# ── wild event shiny roll ─────────────────────────────────────────────────────


def _make_wild_event_mocks():
    from conftest import make_row

    event = make_row(id=1, group_chat_id=-100, species_id=1, message_id=42, caught_by_user_id=None)
    species = make_row(
        species_id=1,
        name="Fox",
        emoji="🦊",
        habitat="woodland",
        catch_rate=0.9,
    )
    user = make_row(user_id=1, username="tester", coins=100, group_chat_id=-100)
    lure_row = make_row(id=5)
    return event, species, user, lure_row


@pytest.mark.asyncio
async def test_wild_event_shiny_sets_flag_when_under_threshold():
    event, species, user, lure_row = _make_wild_event_mocks()

    query = MagicMock()
    query.from_user.id = 1
    query.from_user.username = "tester"
    query.data = "wild_catch_1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query

    with patch("handlers.wild_event.db.get_wild_event", return_value=event), patch(
        "handlers.wild_event.db.get_user", return_value=user
    ), patch("handlers.wild_event.db.get_species", return_value=species), patch(
        "handlers.wild_event.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.wild_event.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.wild_event.db.get_oldest_purchase", return_value=lure_row
    ), patch(
        "handlers.wild_event.db.consume_purchase"
    ), patch(
        "handlers.wild_event.db.claim_wild_event", return_value=True
    ), patch(
        "handlers.wild_event.db.add_animal"
    ), patch(
        "handlers.wild_event.db.set_animal_shiny"
    ) as mock_shiny, patch(
        "handlers.wild_event.db.set_animal_stats"
    ), patch(
        "handlers.wild_event.random.random", return_value=0.010
    ), patch(  # first call: catch roll (0.010 < 0.9 → success); second: shiny (< 0.015)
        "handlers.wild_event.check_achievements", new_callable=AsyncMock
    ):
        await wild_event_callback(update, MagicMock())

    mock_shiny.assert_called_once()
    answer_text = query.answer.call_args[0][0]
    assert "⭐" in answer_text


@pytest.mark.asyncio
async def test_wild_event_shiny_skips_flag_when_over_threshold():
    event, species, user, lure_row = _make_wild_event_mocks()

    query = MagicMock()
    query.from_user.id = 1
    query.from_user.username = "tester"
    query.data = "wild_catch_1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query

    with patch("handlers.wild_event.db.get_wild_event", return_value=event), patch(
        "handlers.wild_event.db.get_user", return_value=user
    ), patch("handlers.wild_event.db.get_species", return_value=species), patch(
        "handlers.wild_event.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.wild_event.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.wild_event.db.get_oldest_purchase", return_value=lure_row
    ), patch(
        "handlers.wild_event.db.consume_purchase"
    ), patch(
        "handlers.wild_event.db.claim_wild_event", return_value=True
    ), patch(
        "handlers.wild_event.db.add_animal"
    ), patch(
        "handlers.wild_event.db.set_animal_shiny"
    ) as mock_shiny, patch(
        "handlers.wild_event.db.set_animal_stats"
    ), patch(
        "handlers.wild_event.random.random", return_value=0.020
    ), patch(  # catch succeeds (0.020 < 0.9); shiny roll: 0.020 >= 0.015 → no shiny
        "handlers.wild_event.check_achievements", new_callable=AsyncMock
    ):
        await wild_event_callback(update, MagicMock())

    mock_shiny.assert_not_called()
    answer_text = query.answer.call_args[0][0]
    assert "⭐" not in answer_text
