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
async def test_catch_lure_callback_does_not_consume_lure_when_no_species_found():
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
    ):
        await catch_lure_callback(update, ctx)

    mock_consume.assert_not_called()
    query.answer.assert_called_once()
    assert "try again" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_catch_lure_none_deducts_cost_and_uses_base_multiplier():
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
        "handlers.catch.db.add_coins"
    ) as mock_add_coins, patch(
        "handlers.catch.roll_encounter", return_value="common"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[species]
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    mock_get_purchase.assert_not_called()
    mock_consume.assert_not_called()
    mock_add_coins.assert_called_once_with(1, -10)  # NO_LURE_COST = 10
    pending = ctx.user_data.get("pending_catch")
    assert pending is not None
    assert pending["lure_multiplier"] == 1.0


@pytest.mark.asyncio
async def test_catch_lure_none_rejects_when_insufficient_coins():
    query = MagicMock()
    query.from_user.id = 1
    query.data = "catch_lure_none"
    query.answer = AsyncMock()

    update = MagicMock()
    update.callback_query = query

    ctx = MagicMock()
    ctx.user_data = {}

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 5,  # less than NO_LURE_COST=10
            "catch_net_active": 0,
            "rare_magnet_active": 0,
            "epic_magnet_active": 0,
        },
    ), patch("handlers.catch.db.add_coins") as mock_add_coins:
        await catch_lure_callback(update, ctx)

    mock_add_coins.assert_not_called()
    query.answer.assert_called_once()
    assert query.answer.call_args[1].get("show_alert") is True


@pytest.mark.asyncio
async def test_catch_lure_mythic_produces_only_epic_or_legendary():
    """Mythic lure must request only epic or legendary candidates (never common/rare)."""
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
        "name": "Phoenix",
        "emoji": "🐦‍🔥",
        "rarity": "epic",
        "habitat": "mythic",
        "catch_rate": 0.35,
        "catch_cost": 80,
    }

    rarity_seen = []

    def capture_candidates(rarity, habitat):
        rarity_seen.append(rarity)
        return [species]

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
        "handlers.catch.db.get_species_candidates", side_effect=capture_candidates
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    assert len(rarity_seen) == 1
    assert rarity_seen[0] in ("epic", "legendary")


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


# ── catch_callback other paths ────────────────────────────────────────────────


def _make_catch_callback(data="catch_attempt_1", pending=None):
    query = MagicMock()
    query.from_user.id = 1
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.user_data = {"pending_catch": pending} if pending else {}
    return update, query, ctx


@pytest.mark.asyncio
async def test_catch_cancel():
    update, query, ctx = _make_catch_callback(data="catch_cancel", pending=_make_pending())
    await catch_callback(update, ctx)
    query.answer.assert_called_once_with("Cancelled")
    assert "cancelled" in query.edit_message_text.call_args[0][0].lower()
    assert ctx.user_data.get("pending_catch") is None


@pytest.mark.asyncio
async def test_catch_skip():
    update, query, ctx = _make_catch_callback(data="catch_skip", pending=_make_pending())
    await catch_callback(update, ctx)
    query.answer.assert_called_once_with("Skipped")
    assert "let it go" in query.edit_message_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_catch_no_pending():
    update, query, ctx = _make_catch_callback(data="catch_attempt_1", pending=None)
    await catch_callback(update, ctx)
    query.answer.assert_called_once()
    assert "no active catch" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_catch_outdated_species_id():
    pending = _make_pending(species_id=1)
    update, query, ctx = _make_catch_callback(data="catch_attempt_999", pending=pending)
    await catch_callback(update, ctx)
    assert query.answer.call_args[1].get("show_alert") is True
    assert "outdated" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_catch_expired():
    import datetime

    old_pending = {
        "species_id": 1,
        "catch_rate": 0.9,
        "catch_cost": 20,
        "rarity": "common",
        "name": "Mouse",
        "emoji": "🐭",
        "at": (
            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            - datetime.timedelta(hours=2)
        ).isoformat(),
        "message_id": 42,
        "lure_multiplier": 1.0,
    }
    update, query, ctx = _make_catch_callback(data="catch_attempt_1", pending=old_pending)
    await catch_callback(update, ctx)
    query.answer.assert_called_once()
    assert (
        "time" in query.answer.call_args[0][0].lower()
        or "slow" in query.answer.call_args[0][0].lower()
    )


@pytest.mark.asyncio
async def test_catch_insufficient_coins():
    pending = _make_pending(species_id=1)
    update, query, ctx = _make_catch_callback(data="catch_attempt_1", pending=pending)
    with patch(
        "handlers.catch.db.get_user",
        return_value={"coins": 0, "lucky_catch_active": 0, "catch_net_active": 0},
    ):
        await catch_callback(update, ctx)
    query.answer.assert_called_once()
    assert (
        "enough" in query.answer.call_args[0][0].lower()
        or "need" in query.answer.call_args[0][0].lower()
    )


@pytest.mark.asyncio
async def test_catch_miss():
    pending = _make_pending(species_id=1)
    update, query, ctx = _make_catch_callback(data="catch_attempt_1", pending=pending)
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
        "handlers.catch.roll_catch", return_value=False
    ):
        await catch_callback(update, ctx)
    query.answer.assert_called_once_with("It escaped...")
    assert "broke free" in query.edit_message_text.call_args[0][0]


@pytest.mark.asyncio
async def test_catch_lure_callback_catch_net_gives_legendary():
    """catch_net_active overrides rarity to legendary."""
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
        "species_id": 10,
        "name": "Dragon",
        "emoji": "🐉",
        "rarity": "legendary",
        "habitat": "mythic",
        "catch_rate": 0.1,
        "catch_cost": 100,
    }

    rarity_used = []

    def capture(rarity, habitat):
        rarity_used.append(rarity)
        return [species]

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 200,
            "catch_net_active": 1,
            "rare_magnet_active": 0,
            "epic_magnet_active": 0,
        },
    ), patch("handlers.catch.db.add_coins"), patch(
        "handlers.catch.roll_encounter", return_value="common"
    ), patch(
        "handlers.catch.db.get_species_candidates", side_effect=capture
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    assert rarity_used[0] == "legendary"


# ── enc_catch_bonus ───────────────────────────────────────────────────────────


def _make_lure_callback_setup(habitat="woodland", enc_level=1, species=None):
    """Build the shared setup for catch_lure_callback tests."""
    query = MagicMock()
    query.from_user.id = 1
    query.data = f"catch_lure_{habitat}"
    query.answer = AsyncMock()
    msg = MagicMock()
    msg.message_id = 77
    query.edit_message_text = AsyncMock(return_value=msg)
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.user_data = {}

    lure_purchase = MagicMock()
    lure_purchase.__getitem__ = lambda self, key: 42 if key == "id" else None

    if species is None:
        species = {
            "species_id": 5,
            "name": "Fox",
            "emoji": "🦊",
            "rarity": "rare",
            "habitat": habitat,
            "catch_rate": 0.6,
            "catch_cost": 60,
        }

    patches = dict(
        get_user={
            "coins": 200,
            "catch_net_active": 0,
            "rare_magnet_active": 0,
            "epic_magnet_active": 0,
        },
        enc_level=enc_level,
        species=species,
        purchase=lure_purchase,
    )
    return update, query, ctx, patches


@pytest.mark.asyncio
async def test_enc_catch_bonus_stored_in_pending_for_level_6():
    from game.species_data import ENCLOSURE_LEVELS

    update, query, ctx, p = _make_lure_callback_setup(enc_level=6)

    with patch("handlers.catch.db.get_user", return_value=p["get_user"]), patch(
        "handlers.catch.db.get_oldest_purchase", return_value=p["purchase"]
    ), patch("handlers.catch.db.consume_purchase"), patch(
        "handlers.catch.db.get_enclosure_level", return_value=6
    ), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.roll_encounter", return_value="rare"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[p["species"]]
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    pending = ctx.user_data.get("pending_catch")
    assert pending is not None
    assert pending["enc_catch_bonus"] == pytest.approx(ENCLOSURE_LEVELS[6]["catch_rate_bonus"])
    assert pending["enc_catch_bonus"] == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_enc_catch_bonus_is_zero_for_level_1():
    update, query, ctx, p = _make_lure_callback_setup(enc_level=1)

    with patch("handlers.catch.db.get_user", return_value=p["get_user"]), patch(
        "handlers.catch.db.get_oldest_purchase", return_value=p["purchase"]
    ), patch("handlers.catch.db.consume_purchase"), patch(
        "handlers.catch.db.get_enclosure_level", return_value=1
    ), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.roll_encounter", return_value="rare"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[p["species"]]
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    pending = ctx.user_data.get("pending_catch")
    assert pending is not None
    assert pending["enc_catch_bonus"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_enc_catch_bonus_zero_for_no_lure():
    """No-lure catch must never have a catch bonus (enc_catch_bonus=0.0)."""
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
    ), patch("handlers.catch.db.add_coins"), patch(
        "handlers.catch.roll_encounter", return_value="common"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[species]
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    pending = ctx.user_data.get("pending_catch")
    assert pending is not None
    assert pending["enc_catch_bonus"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_catch_rate_display_includes_enc_bonus():
    """With level 6 enclosure: rare (0.6) × 1.5 lure + 0.05 bonus = 95%, not 90%."""
    update, query, ctx, p = _make_lure_callback_setup(enc_level=6)

    with patch("handlers.catch.db.get_user", return_value=p["get_user"]), patch(
        "handlers.catch.db.get_oldest_purchase", return_value=p["purchase"]
    ), patch("handlers.catch.db.consume_purchase"), patch(
        "handlers.catch.db.get_enclosure_level", return_value=6
    ), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.roll_encounter", return_value="rare"
    ), patch(
        "handlers.catch.db.get_species_candidates", return_value=[p["species"]]
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_lure_callback(update, ctx)

    text = query.edit_message_text.call_args[0][0]
    assert "95%" in text
    assert "90%" not in text


@pytest.mark.asyncio
async def test_catch_callback_applies_enc_catch_bonus_additively():
    captured = []

    def capture_roll(rate):
        captured.append(rate)
        return True

    pending = {**_make_pending(species_id=1, lure_multiplier=1.0), "enc_catch_bonus": 0.05}
    update, query, ctx = _make_catch_callback(data="catch_attempt_1", pending=pending)

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 500,
            "lucky_catch_active": 0,
            "catch_net_active": 0,
        },
    ), patch("handlers.catch.db.get_species_habitat", return_value="woodland"), patch(
        "handlers.catch.db.get_animal_count_by_habitat", return_value=0
    ), patch(
        "handlers.catch.db.get_enclosure_level", return_value=6
    ), patch(
        "handlers.catch.db.add_coins"
    ), patch(
        "handlers.catch.db.add_animal"
    ), patch(
        "handlers.catch.db.set_animal_shiny"
    ), patch(
        "handlers.catch.db.set_animal_stats"
    ), patch(
        "handlers.catch.roll_catch", side_effect=capture_roll
    ), patch(
        "handlers.catch.check_achievements", new_callable=AsyncMock
    ):
        await catch_callback(update, ctx)

    # catch_rate = 0.9 * 1.0 + 0.05 = 0.95
    assert len(captured) == 1
    assert captured[0] == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_catch_callback_enc_catch_bonus_defaults_to_zero():
    """Old-style pending dicts without enc_catch_bonus must work unchanged."""
    captured = []

    def capture_roll(rate):
        captured.append(rate)
        return True

    pending = _make_pending(species_id=1, lure_multiplier=1.0)
    assert "enc_catch_bonus" not in pending

    update, query, ctx = _make_catch_callback(data="catch_attempt_1", pending=pending)

    with patch(
        "handlers.catch.db.get_user",
        return_value={
            "coins": 500,
            "lucky_catch_active": 0,
            "catch_net_active": 0,
        },
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
    ), patch(
        "handlers.catch.db.set_animal_stats"
    ), patch(
        "handlers.catch.roll_catch", side_effect=capture_roll
    ), patch(
        "handlers.catch.check_achievements", new_callable=AsyncMock
    ):
        await catch_callback(update, ctx)

    # catch_rate = 0.9 * 1.0 + 0.0 = 0.9
    assert len(captured) == 1
    assert captured[0] == pytest.approx(0.9)
