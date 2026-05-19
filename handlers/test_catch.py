import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.catch import catch_command, catch_lure_callback, catch_callback, LURE_MULTIPLIER


@pytest.fixture(autouse=True)
def stub_catch_db(monkeypatch):
    monkeypatch.setattr("handlers.catch.db.set_lucky_catch", lambda *a: None)
    monkeypatch.setattr("handlers.catch.db.set_rare_magnet", lambda *a: None)
    monkeypatch.setattr("handlers.catch.db.get_catch_message", lambda *a: (None, None))
    monkeypatch.setattr("handlers.catch.db.set_catch_message", lambda *a: None)


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, inner


def _make_pending(species_id=1, lure_multiplier=1.5):
    return {
        "species_id": species_id,
        "catch_rate": 0.9,
        "catch_cost": 20,
        "rarity": "common",
        "name": "Mouse",
        "emoji": "🐭",
        "at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(),
        "message_id": 42,
        "lure_multiplier": lure_multiplier,
    }


# ── catch_command ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_catch_command_shows_no_lure_button_when_no_lures():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock(return_value=MagicMock(message_id=99))
    update.effective_chat.id = 1

    ctx = MagicMock()
    ctx.user_data = {}

    with patch("handlers.catch.db.get_user", return_value={"coins": 200}), patch(
        "handlers.catch.db.get_item_counts", return_value={}
    ), patch("handlers.catch.db.get_catch_message", return_value=(None, None)), patch(
        "handlers.catch.db.set_catch_message"
    ):
        await catch_command(update, ctx)

    update.message.reply_text.assert_called_once()
    call_kwargs = update.message.reply_text.call_args[1]
    kb = call_kwargs.get("reply_markup")
    assert kb is not None
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    assert any(btn.callback_data == "catch_lure_none" for btn in buttons)


@pytest.mark.asyncio
async def test_catch_command_shows_lure_keyboard_when_lures_held():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.user_data = {}

    keyboard = MagicMock()

    with patch("handlers.catch.db.get_user", return_value={"coins": 200}), patch(
        "handlers.catch.db.get_item_counts", return_value={"lure_woodland": 1}
    ), patch("handlers.catch.lure_keyboard", return_value=keyboard):
        await catch_command(update, ctx)

    update.message.reply_text.assert_called_once()
    call_kwargs = update.message.reply_text.call_args[1]
    assert call_kwargs.get("reply_markup") is keyboard


# ── catch_lure_callback ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_catch_lure_callback_blocks_when_lure_not_in_inventory():
    query = MagicMock()
    query.from_user.id = 1
    query.data = "catch_lure_woodland"
    query.answer = AsyncMock()

    update = MagicMock()
    update.callback_query = query
    update.effective_chat.id = 99

    ctx = MagicMock()
    ctx.user_data = {}

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 200,
            "catch_net_active": 0,
            "rare_magnet_active": 0,
            "epic_magnet_active": 0,
        },
    ), patch("handlers.catch.db.get_oldest_purchase", return_value=None):
        await catch_lure_callback(update, ctx)

    query.answer.assert_called_once()
    call_kwargs = query.answer.call_args[1]
    assert call_kwargs.get("show_alert") is True


@pytest.mark.asyncio
async def test_catch_lure_callback_generates_encounter_and_stores_pending():
    query = MagicMock()
    query.from_user.id = 1
    query.data = "catch_lure_woodland"
    query.answer = AsyncMock()
    msg = MagicMock()
    msg.message_id = 77
    query.edit_message_text = AsyncMock(return_value=msg)

    update = MagicMock()
    update.callback_query = query
    update.effective_chat.id = 99

    ctx = MagicMock()
    ctx.user_data = {}

    lure_purchase = MagicMock()
    lure_purchase.__getitem__ = lambda self, key: 42 if key == "id" else None

    species = {
        "species_id": 5,
        "name": "Fox",
        "emoji": "🦊",
        "rarity": "rare",
        "catch_rate": 0.6,
        "catch_cost": 40,
    }

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 200,
            "catch_net_active": 0,
            "rare_magnet_active": 0,
            "epic_magnet_active": 0,
        },
    ), patch("handlers.catch.db.get_oldest_purchase", return_value=lure_purchase), patch(
        "handlers.catch.db.consume_purchase"
    ), patch(
        "handlers.catch.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.roll_encounter", return_value="rare"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[species]
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    pending = ctx.user_data.get("pending_catch")
    assert pending is not None
    assert pending["species_id"] == 5
    assert pending["lure_multiplier"] == LURE_MULTIPLIER


@pytest.mark.asyncio
async def test_catch_lure_callback_exhausts_lure_when_no_species_found():
    query = MagicMock()
    query.from_user.id = 1
    query.data = "catch_lure_woodland"
    query.answer = AsyncMock()

    update = MagicMock()
    update.callback_query = query

    ctx = MagicMock()
    ctx.user_data = {}

    lure_purchase = MagicMock()
    lure_purchase.__getitem__ = lambda self, key: 42 if key == "id" else None

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 200,
            "catch_net_active": 0,
            "rare_magnet_active": 0,
            "epic_magnet_active": 0,
        },
    ), patch("handlers.catch.db.get_oldest_purchase", return_value=lure_purchase), patch(
        "handlers.catch.db.consume_purchase"
    ) as mock_consume, patch(
        "handlers.catch.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.roll_encounter", return_value="rare"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[]
    ), patch(
        "handlers.catch.db.record_purchase"
    ) as mock_refund:
        await catch_lure_callback(update, ctx)

    mock_consume.assert_called_once()
    mock_refund.assert_not_called()


@pytest.mark.asyncio
async def test_catch_lure_none_does_not_consume_lure_and_uses_base_multiplier():
    query = MagicMock()
    query.from_user.id = 1
    query.data = "catch_lure_none"
    query.answer = AsyncMock()
    msg = MagicMock()
    msg.message_id = 55
    query.edit_message_text = AsyncMock(return_value=msg)

    update = MagicMock()
    update.callback_query = query

    ctx = MagicMock()
    ctx.user_data = {}

    species = {
        "species_id": 7,
        "name": "Duck",
        "emoji": "🦆",
        "rarity": "common",
        "habitat": "aquatic",
        "catch_rate": 0.9,
        "catch_cost": 20,
    }

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 100,
            "catch_net_active": 0,
            "rare_magnet_active": 0,
            "epic_magnet_active": 0,
        },
    ), patch("handlers.catch.db.get_oldest_purchase") as mock_get_purchase, patch(
        "handlers.catch.db.consume_purchase"
    ) as mock_consume, patch(
        "handlers.catch.roll_encounter", return_value="common"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[species]
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    mock_get_purchase.assert_not_called()
    mock_consume.assert_not_called()
    pending = ctx.user_data.get("pending_catch")
    assert pending is not None
    assert pending["lure_multiplier"] == 1.0


@pytest.mark.asyncio
async def test_catch_lure_mythic_forces_legendary_rarity():
    """Mythic lure must override roll_encounter() and always request legendary candidates."""
    query = MagicMock()
    query.from_user.id = 1
    query.data = "catch_lure_mythic"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock()
    update.callback_query = query

    ctx = MagicMock()
    ctx.user_data = {}

    lure_purchase = MagicMock()
    lure_purchase.__getitem__ = lambda self, key: 42 if key == "id" else None

    species = {
        "species_id": 99,
        "name": "Unicorn",
        "emoji": "🦄",
        "rarity": "legendary",
        "habitat": "mythic",
        "catch_rate": 0.10,
        "catch_cost": 200,
    }

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 500,
            "catch_net_active": 0,
            "rare_magnet_active": 0,
            "epic_magnet_active": 0,
        },
    ), patch("handlers.catch.db.get_oldest_purchase", return_value=lure_purchase), patch(
        "handlers.catch.db.consume_purchase"
    ), patch(
        "handlers.catch.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.roll_encounter", return_value="common"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[species]
    ) as mock_candidates:
        await catch_lure_callback(update, ctx)

    mock_candidates.assert_called_once_with("legendary", "mythic")


# ── catch_callback capacity gate ──────────────────────────────────────────────


class TestCatchCapacityGate:
    @pytest.mark.asyncio
    async def test_catch_blocked_when_enclosure_full(self):
        query = MagicMock()
        query.from_user.id = 1
        query.data = "catch_attempt_1"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        ctx = MagicMock()
        ctx.user_data = {"pending_catch": _make_pending(species_id=1)}

        with patch(
            "handlers.catch.db.get_user",
            return_value={
                "coins": 500,
                "lucky_catch_active": 0,
                "catch_net_active": 0,
                "rare_magnet_active": 0,
            },
        ), patch("handlers.catch.db.get_conn"), patch(
            "handlers.catch.roll_catch", return_value=True
        ), patch(
            "handlers.catch.db.get_species_habitat", return_value="woodland"
        ), patch(
            "handlers.catch.db.get_animal_count_by_habitat", return_value=3
        ), patch(
            "handlers.catch.db.get_enclosure_level", return_value=1
        ):
            await catch_callback(update, ctx)

        query.edit_message_text.assert_called_once()
        msg = query.edit_message_text.call_args[0][0]
        assert "full" in msg.lower() or "enclosure" in msg.lower()

    @pytest.mark.asyncio
    async def test_catch_succeeds_when_space_available(self):
        query = MagicMock()
        query.from_user.id = 1
        query.data = "catch_attempt_1"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        ctx = MagicMock()
        ctx.user_data = {"pending_catch": _make_pending(species_id=1)}

        cm, inner = _make_conn_mock()

        with patch(
            "handlers.catch.db.get_user",
            return_value={
                "coins": 500,
                "lucky_catch_active": 0,
                "catch_net_active": 0,
                "rare_magnet_active": 0,
            },
        ), patch("handlers.catch.db.get_conn", return_value=cm), patch(
            "handlers.catch.roll_catch", return_value=True
        ), patch(
            "handlers.catch.db.get_species_habitat", return_value="woodland"
        ), patch(
            "handlers.catch.db.get_animal_count_by_habitat", return_value=1
        ), patch(
            "handlers.catch.db.get_enclosure_level", return_value=1
        ), patch(
            "handlers.catch.check_achievements", new_callable=AsyncMock
        ):
            await catch_callback(update, ctx)

        query.answer.assert_called_with("Caught!")
