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
