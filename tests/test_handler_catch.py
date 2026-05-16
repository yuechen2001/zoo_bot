import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.catch import catch_command, ENCOUNTER_FEE


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, inner


# ── Fix 5: flat -10 encounter fee ─────────────────────────────────────────────


def test_encounter_fee_is_10():
    assert ENCOUNTER_FEE == 10


@pytest.mark.asyncio
async def test_catch_rejects_when_insufficient_coins():
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.user_data = {}

    with patch("handlers.catch.db.get_user", return_value={"coins": 5}):
        await catch_command(update, ctx)

    update.message.reply_text.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert str(ENCOUNTER_FEE) in reply or "Not enough" in reply


@pytest.mark.asyncio
async def test_catch_deducts_encounter_fee_upfront():
    """Fix 5: ENCOUNTER_FEE deducted immediately on /catch, before the user decides to attempt."""
    cm, inner = _make_conn_mock()
    deducted = []

    def capture_execute(query, params=None):
        if params:
            deducted.append((query, params))

    inner.execute = MagicMock(side_effect=capture_execute)

    species = {
        "species_id": 1,
        "name": "Mouse",
        "emoji": "🐭",
        "rarity": "common",
        "catch_rate": 0.9,
        "catch_cost": 20,
    }

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.user_data = {}

    with patch("handlers.catch.db.get_user", side_effect=[{"coins": 100}, {"coins": 90}]), patch(
        "handlers.catch.db.get_conn", return_value=cm
    ), patch("handlers.catch.roll_encounter", return_value="common"), patch(
        "handlers.catch.pick_species", return_value=species
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_command(update, ctx)

    # An UPDATE that deducts ENCOUNTER_FEE must have been executed
    fee_deductions = [
        (q, p) for q, p in deducted if "UPDATE users SET coins" in q and ENCOUNTER_FEE in p
    ]
    assert len(fee_deductions) >= 1, "ENCOUNTER_FEE was not deducted during /catch"


@pytest.mark.asyncio
async def test_catch_stores_pending_catch_in_context():
    """After /catch, pending_catch should be stored in ctx.user_data."""
    cm, _ = _make_conn_mock()

    species = {
        "species_id": 3,
        "name": "Fox",
        "emoji": "🦊",
        "rarity": "rare",
        "catch_rate": 0.6,
        "catch_cost": 60,
    }

    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()

    ctx = MagicMock()
    ctx.user_data = {}

    with patch("handlers.catch.db.get_user", side_effect=[{"coins": 100}, {"coins": 90}]), patch(
        "handlers.catch.db.get_conn", return_value=cm
    ), patch("handlers.catch.roll_encounter", return_value="rare"), patch(
        "handlers.catch.pick_species", return_value=species
    ), patch(
        "handlers.catch.catch_keyboard", return_value=MagicMock()
    ):
        await catch_command(update, ctx)

    pending = ctx.user_data.get("pending_catch")
    assert pending is not None
    assert pending["species_id"] == 3
    assert pending["rarity"] == "rare"


class TestCatchCapacityGate:
    def _make_pending(self, species_id=1):
        import datetime

        return {
            "species_id": species_id,
            "catch_rate": 0.9,
            "catch_cost": 20,
            "rarity": "common",
            "name": "Mouse",
            "emoji": "🐭",
            "at": datetime.datetime.utcnow().isoformat(),
            "message_id": 42,
        }

    @pytest.mark.asyncio
    async def test_catch_blocked_when_enclosure_full(self):
        from handlers.catch import catch_callback

        query = MagicMock()
        query.from_user.id = 1
        query.data = "catch_attempt_1"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        ctx = MagicMock()
        ctx.user_data = {"pending_catch": self._make_pending(species_id=1)}

        with patch("handlers.catch.db.get_user", return_value={"coins": 500}), patch(
            "handlers.catch.db.get_conn"
        ), patch("handlers.catch.roll_catch", return_value=True), patch(
            "handlers.catch.db.get_species_habitat", return_value="woodland"
        ), patch(
            "handlers.catch.db.get_animal_count_by_habitat", return_value=3
        ), patch(
            "handlers.catch.db.get_enclosure_level", return_value=1
        ):
            await catch_callback(update, ctx)

        # Should show enclosure full message, not a successful catch
        query.edit_message_text.assert_called_once()
        msg = query.edit_message_text.call_args[0][0]
        assert "full" in msg.lower() or "enclosure" in msg.lower()

    @pytest.mark.asyncio
    async def test_catch_succeeds_when_space_available(self):
        from handlers.catch import catch_callback

        query = MagicMock()
        query.from_user.id = 1
        query.data = "catch_attempt_1"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        ctx = MagicMock()
        ctx.user_data = {"pending_catch": self._make_pending(species_id=1)}

        cm, inner = _make_conn_mock()

        with patch("handlers.catch.db.get_user", return_value={"coins": 500}), patch(
            "handlers.catch.db.get_conn", return_value=cm
        ), patch("handlers.catch.roll_catch", return_value=True), patch(
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
