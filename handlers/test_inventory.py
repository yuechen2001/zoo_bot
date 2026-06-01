import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.inventory import inventory_command, inventory_callback
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


def _make_update(args=None):
    update = MagicMock()
    update.effective_user.id = 1
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args or []
    ctx.user_data = {}
    return update, ctx


def _make_user(**kw):
    defaults = {
        "user_id": 1,
        "coins": 500,
        "lucky_catch_active": 0,
        "mood_booster_active": 0,
        "catch_net_active": 0,
        "active_title": None,
    }
    return make_row(**{**defaults, **kw})


def _purchase_row():
    return make_row(id=1)


def _breed_row(hours_from_now=5):
    ready_at = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        + datetime.timedelta(hours=hours_from_now)
    ).isoformat()
    return make_row(id=1, ready_at=ready_at)


def _make_callback(data):
    query = MagicMock()
    query.from_user.id = 1
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query, MagicMock()


# ── display ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inventory_empty_bag():
    update, ctx = _make_update()
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_item_counts", return_value={}
    ), patch("handlers.inventory.db.get_owned_title_keys", return_value=[]):
        await inventory_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "empty" in reply.lower()
    assert "/store" in reply


@pytest.mark.asyncio
async def test_inventory_no_user():
    update, ctx = _make_update()
    with patch("handlers.inventory.db.get_user", return_value=None):
        await inventory_command(update, ctx)
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_shows_items_in_bag():
    update, ctx = _make_update()
    counts = {"lucky_token": 2, "mega_feed": 1}
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_item_counts", return_value=counts
    ), patch("handlers.inventory.db.get_owned_title_keys", return_value=[]):
        await inventory_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Lucky Token" in reply
    assert "Mega Feed" in reply
    assert "×2" in reply


@pytest.mark.asyncio
async def test_inventory_mega_feed_hint_references_inventory():
    update, ctx = _make_update()
    counts = {"mega_feed": 1}
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_item_counts", return_value=counts
    ), patch("handlers.inventory.db.get_owned_title_keys", return_value=[]):
        await inventory_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "/inventory use mega_feed" in reply


# ── /inventory use <item> ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inventory_use_missing_item_key():
    update, ctx = _make_update(args=["use"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()):
        await inventory_command(update, ctx)
    assert "usage" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_unknown_item():
    update, ctx = _make_update(args=["use", "dragon_egg"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()):
        await inventory_command(update, ctx)
    assert "unknown" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_lure_redirects_to_catch():
    update, ctx = _make_update(args=["use", "lure_woodland"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()):
        await inventory_command(update, ctx)
    assert "/catch" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_inventory_use_lucky_token_not_in_bag():
    update, ctx = _make_update(args=["use", "lucky_token"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=None
    ):
        await inventory_command(update, ctx)
    assert "don't have" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_lucky_token_happy_path():
    update, ctx = _make_update(args=["use", "lucky_token"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.consume_purchase") as mock_consume, patch(
        "handlers.inventory.db.set_lucky_catch"
    ) as mock_set:
        await inventory_command(update, ctx)
    mock_consume.assert_called_once_with(1)
    mock_set.assert_called_once_with(1, True)
    assert "lucky" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_mood_booster_happy_path():
    update, ctx = _make_update(args=["use", "mood_booster"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.consume_purchase") as mock_consume, patch(
        "handlers.inventory.db.set_mood_booster"
    ) as mock_set:
        await inventory_command(update, ctx)
    mock_consume.assert_called_once_with(1)
    mock_set.assert_called_once_with(1, True)
    assert "booster" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_catch_net_happy_path():
    update, ctx = _make_update(args=["use", "catch_net"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.consume_purchase") as mock_consume, patch(
        "handlers.inventory.db.set_catch_net"
    ) as mock_set:
        await inventory_command(update, ctx)
    mock_consume.assert_called_once_with(1)
    mock_set.assert_called_once_with(1, True)
    assert "catch net" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_breed_boost_no_active_breed():
    update, ctx = _make_update(args=["use", "breed_boost"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.get_pending_breed", return_value=None):
        await inventory_command(update, ctx)
    assert "no active breed" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_breed_boost_happy_path():
    update, ctx = _make_update(args=["use", "breed_boost"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch(
        "handlers.inventory.db.get_pending_breed", return_value=_breed_row(hours_from_now=5)
    ), patch(
        "handlers.inventory.db.adjust_breed_time_and_consume"
    ) as mock_adjust:
        await inventory_command(update, ctx)
    mock_adjust.assert_called_once()
    assert "boost" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_rare_magnet_happy_path():
    update, ctx = _make_update(args=["use", "rare_magnet"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.consume_purchase") as mock_consume, patch(
        "handlers.inventory.db.set_rare_magnet"
    ) as mock_set:
        await inventory_command(update, ctx)
    mock_consume.assert_called_once()
    mock_set.assert_called_once_with(_make_user()["user_id"], True)
    assert "magnet" in update.message.reply_text.call_args[0][0].lower()


# ── /inventory use mega_feed ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inventory_use_mega_feed_missing_pos():
    update, ctx = _make_update(args=["use", "mega_feed"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()):
        await inventory_command(update, ctx)
    assert "usage" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_mega_feed_not_in_bag():
    update, ctx = _make_update(args=["use", "mega_feed", "1"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=None
    ):
        await inventory_command(update, ctx)
    assert "don't have" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_mega_feed_animal_not_found():
    update, ctx = _make_update(args=["use", "mega_feed", "99"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.get_animal_by_position", return_value=None), patch(
        "handlers.inventory.db.get_animals", return_value=[]
    ):
        await inventory_command(update, ctx)
    assert "no animal" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_mega_feed_happy_path():
    update, ctx = _make_update(args=["use", "mega_feed", "1"])
    animal = make_row(animal_id="abc", nickname=None, species_name="Mouse", emoji="🐭")
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.get_animal_by_position", return_value=animal), patch(
        "handlers.inventory.db.feed_animal_and_consume"
    ) as mock_feed:
        await inventory_command(update, ctx)
    mock_feed.assert_called_once_with("abc", 1)
    assert "mega feed" in update.message.reply_text.call_args[0][0].lower()


# ── /inventory equip ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inventory_equip_missing_key():
    update, ctx = _make_update(args=["equip"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()):
        await inventory_command(update, ctx)
    assert "usage" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_equip_title_sets_active():
    update, ctx = _make_update(args=["equip", "title_keeper"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.has_purchased", return_value=True
    ), patch("handlers.inventory.db.set_active_title") as mock_set:
        await inventory_command(update, ctx)
    mock_set.assert_called_once_with(1, "title_keeper")


@pytest.mark.asyncio
async def test_inventory_equip_unowned_title_blocked():
    update, ctx = _make_update(args=["equip", "title_legend"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.has_purchased", return_value=False
    ):
        await inventory_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "don't own" in reply.lower() or "buy" in reply.lower()


# ── inventory_callback ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_callback_no_user():
    update, query, ctx = _make_callback("inv_use_lucky_token")
    with patch("handlers.inventory.db.get_user", return_value=None):
        await inventory_callback(update, ctx)
    query.answer.assert_called_once()
    assert "start" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_inv_use_applies_item():
    update, query, ctx = _make_callback("inv_use_lucky_token")
    user = _make_user()
    with patch("handlers.inventory.db.get_user", return_value=user), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.consume_purchase"), patch(
        "handlers.inventory.db.set_lucky_catch"
    ) as mock_set, patch(
        "handlers.inventory.db.get_item_counts", return_value={}
    ), patch(
        "handlers.inventory.db.get_owned_title_keys", return_value=[]
    ):
        await inventory_callback(update, ctx)
    mock_set.assert_called_once_with(1, True)
    query.answer.assert_called_once()
    assert "lucky" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_inv_equip_sets_title():
    update, query, ctx = _make_callback("inv_equip_title_keeper")
    user = _make_user()
    with patch("handlers.inventory.db.get_user", return_value=user), patch(
        "handlers.inventory.db.has_purchased", return_value=True
    ), patch("handlers.inventory.db.set_active_title") as mock_set, patch(
        "handlers.inventory.db.get_item_counts", return_value={}
    ), patch(
        "handlers.inventory.db.get_owned_title_keys", return_value=["title_keeper"]
    ):
        await inventory_callback(update, ctx)
    mock_set.assert_called_once_with(1, "title_keeper")
    query.answer.assert_called_once()
    assert "title" in query.answer.call_args[0][0].lower()


# ── lures and cosmetics in _render ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inventory_shows_lures_in_bag():
    update, ctx = _make_update()
    counts = {"lure_woodland": 2}
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_item_counts", return_value=counts
    ), patch("handlers.inventory.db.get_owned_title_keys", return_value=[]):
        await inventory_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Lures" in reply or "lure" in reply.lower()


# ── remaining _apply items ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inventory_use_epic_magnet_happy_path():
    update, ctx = _make_update(args=["use", "epic_magnet"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.consume_purchase") as mock_consume, patch(
        "handlers.inventory.db.set_epic_magnet"
    ) as mock_set:
        await inventory_command(update, ctx)
    mock_consume.assert_called_once()
    mock_set.assert_called_once_with(1, True)
    assert "epic" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_streak_shield_happy_path():
    update, ctx = _make_update(args=["use", "streak_shield"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.consume_purchase") as mock_consume, patch(
        "handlers.inventory.db.set_streak_shield"
    ) as mock_set:
        await inventory_command(update, ctx)
    mock_consume.assert_called_once()
    mock_set.assert_called_once_with(1, True)
    assert "shield" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_breed_accelerator_no_active_breed():
    update, ctx = _make_update(args=["use", "breed_accelerator"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.inventory.db.get_pending_breed", return_value=None):
        await inventory_command(update, ctx)
    assert "no active breed" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_inventory_use_breed_accelerator_happy_path():
    update, ctx = _make_update(args=["use", "breed_accelerator"])
    with patch("handlers.inventory.db.get_user", return_value=_make_user()), patch(
        "handlers.inventory.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch(
        "handlers.inventory.db.get_pending_breed", return_value=_breed_row(hours_from_now=4)
    ), patch(
        "handlers.inventory.db.adjust_breed_time_and_consume"
    ) as mock_adjust:
        await inventory_command(update, ctx)
    mock_adjust.assert_called_once()
    assert "halved" in update.message.reply_text.call_args[0][0].lower()
