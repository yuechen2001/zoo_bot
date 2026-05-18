import datetime
import pytest
from html.parser import HTMLParser
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.store import store_command, store_callback, _store_text
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
    return update, ctx


def _make_user(**kw):
    defaults = {
        "user_id": 1,
        "username": "alice",
        "group_chat_id": -100,
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


# ── _store_text HTML smoke tests ─────────────────────────────────────────────

_ALLOWED_TAGS = {"b", "i", "code"}


class _StrictHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        assert tag in _ALLOWED_TAGS, f"unexpected tag <{tag}>"

    def handle_endtag(self, tag):
        assert tag in _ALLOWED_TAGS, f"unexpected closing tag </{tag}>"


def _assert_html(text: str):
    _StrictHTMLParser().feed(text)
    assert "<b>" in text, "expected HTML bold tags, got Markdown or plain text"
    assert "*" not in text, "raw Markdown bold marker found — parse_mode mismatch"
    assert "&lt;" in text, "angle bracket in code span should be escaped as &lt;"


def test_store_text_html_no_badges():
    with patch("handlers.store.db.get_consumable_counts", return_value={}), patch(
        "handlers.store.db.get_user",
        return_value=_make_user(),
    ):
        _assert_html(_store_text(1))


def test_store_text_html_with_badges():
    counts = {key: 2 for key in ["lucky_token", "mood_booster", "catch_net", "mega_feed"]}
    with patch("handlers.store.db.get_consumable_counts", return_value=counts), patch(
        "handlers.store.db.get_user",
        return_value=_make_user(lucky_catch_active=1, mood_booster_active=1, catch_net_active=1),
    ):
        text = _store_text(1)
    _assert_html(text)
    assert "<i>" in text, "expected italic badge tags"


# ── store_command display ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_shows_items():
    update, ctx = _make_update(args=[])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_owned_title_keys", return_value=set()
    ), patch("handlers.store.db.get_consumable_counts", return_value={}):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Mega Feed" in reply
    assert "Lucky Token" in reply
    assert "Zookeeper" in reply


@pytest.mark.asyncio
async def test_store_no_user():
    update, ctx = _make_update()
    with patch("handlers.store.db.get_user", return_value=None):
        await store_command(update, ctx)
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_store_unknown_subcommand_shows_store():
    update, ctx = _make_update(args=["xyz"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_owned_title_keys", return_value=set()
    ), patch("handlers.store.db.get_consumable_counts", return_value={}):
        await store_command(update, ctx)
    assert "Mega Feed" in update.message.reply_text.call_args[0][0]


# ── store_command /store buy ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_buy_missing_key():
    update, ctx = _make_update(args=["buy"])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    assert "usage" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_store_buy_unknown_item():
    update, ctx = _make_update(args=["buy", "dragon_egg"])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "unknown" in reply.lower() or "dragon_egg" in reply.lower()


@pytest.mark.asyncio
async def test_store_buy_insufficient_coins():
    update, ctx = _make_update(args=["buy", "mega_feed"])
    with patch("handlers.store.db.get_user", return_value=_make_user(coins=5)):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "not enough" in reply.lower() or "coins" in reply.lower()


@pytest.mark.asyncio
async def test_store_buy_consumable_records_purchase():
    update, ctx = _make_update(args=["buy", "lucky_token"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.deduct_coins"
    ) as mock_deduct, patch("handlers.store.db.record_purchase") as mock_record:
        await store_command(update, ctx)
    mock_deduct.assert_called_once_with(1, 50)
    mock_record.assert_called_once_with(1, "lucky_token")
    reply = update.message.reply_text.call_args[0][0]
    assert "Lucky Token" in reply
    assert "bag" in reply.lower() or "store use" in reply.lower()


@pytest.mark.asyncio
async def test_store_buy_cosmetic_records_purchase():
    update, ctx = _make_update(args=["buy", "title_keeper"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=False
    ), patch("handlers.store.db.deduct_coins") as mock_deduct, patch(
        "handlers.store.db.record_purchase"
    ) as mock_record:
        await store_command(update, ctx)
    mock_deduct.assert_called_once()
    mock_record.assert_called_once_with(1, "title_keeper")
    reply = update.message.reply_text.call_args[0][0]
    assert "Zookeeper" in reply


@pytest.mark.asyncio
async def test_store_buy_cosmetic_already_owned():
    update, ctx = _make_update(args=["buy", "title_keeper"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=True
    ):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "already own" in reply.lower() or "equip" in reply.lower()


# ── store_command /store equip ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_equip_missing_key():
    update, ctx = _make_update(args=["equip"])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    assert "usage" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_store_equip_title_sets_active():
    update, ctx = _make_update(args=["equip", "title_keeper"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=True
    ), patch("handlers.store.db.set_active_title") as mock_set:
        await store_command(update, ctx)
    mock_set.assert_called_once_with(1, "title_keeper")


@pytest.mark.asyncio
async def test_store_equip_unowned_title_blocked():
    update, ctx = _make_update(args=["equip", "title_legend"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=False
    ):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "don't own" in reply.lower() or "buy" in reply.lower()


# ── store_command /store use edge cases ──────────────────────────────────────


@pytest.mark.asyncio
async def test_store_use_missing_key():
    update, ctx = _make_update(args=["use"])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    assert "usage" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_store_use_unknown_item():
    update, ctx = _make_update(args=["use", "dragon_egg"])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    assert "unknown" in update.message.reply_text.call_args[0][0].lower()


# ── /store use mega_feed ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_use_mega_feed_not_in_bag():
    update, ctx = _make_update(args=["use", "mega_feed", "1"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=None
    ):
        await store_command(update, ctx)
    assert "don't have" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_mega_feed_animal_not_found():
    update, ctx = _make_update(args=["use", "mega_feed", "99"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.store.db.get_animal_by_position", return_value=None), patch(
        "handlers.store.db.get_animals", return_value=[]
    ):
        await store_command(update, ctx)
    assert "no animal" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_mega_feed_happy_path():
    update, ctx = _make_update(args=["use", "mega_feed", "1"])
    animal = make_row(animal_id="abc", nickname=None, species_name="Mouse", emoji="🐭")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.store.db.get_animal_by_position", return_value=animal), patch(
        "handlers.store.db.feed_animal_and_consume"
    ) as mock_feed:
        await store_command(update, ctx)
    mock_feed.assert_called_once_with("abc", 1)
    assert "mega feed" in update.message.reply_text.call_args[0][0].lower()


# ── /store use breed_boost ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_use_breed_boost_not_in_bag():
    update, ctx = _make_update(args=["use", "breed_boost"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=None
    ):
        await store_command(update, ctx)
    assert "don't have" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_breed_boost_no_active_breed():
    update, ctx = _make_update(args=["use", "breed_boost"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.store.db.get_pending_breed", return_value=None):
        await store_command(update, ctx)
    assert "no active breed" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_breed_boost_happy_path():
    update, ctx = _make_update(args=["use", "breed_boost"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch(
        "handlers.store.db.get_pending_breed", return_value=_breed_row(hours_from_now=5)
    ), patch(
        "handlers.store.db.adjust_breed_time_and_consume"
    ) as mock_adjust:
        await store_command(update, ctx)
    mock_adjust.assert_called_once()
    assert "boost" in update.message.reply_text.call_args[0][0].lower()


# ── /store use lucky_token ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_use_lucky_token_not_in_bag():
    update, ctx = _make_update(args=["use", "lucky_token"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=None
    ):
        await store_command(update, ctx)
    assert "don't have" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_lucky_token_happy_path():
    update, ctx = _make_update(args=["use", "lucky_token"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.store.db.consume_purchase") as mock_consume, patch(
        "handlers.store.db.set_lucky_catch"
    ) as mock_set:
        await store_command(update, ctx)
    mock_consume.assert_called_once_with(1)
    mock_set.assert_called_once_with(1, True)
    assert "lucky" in update.message.reply_text.call_args[0][0].lower()


# ── /store use mood_booster ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_use_mood_booster_not_in_bag():
    update, ctx = _make_update(args=["use", "mood_booster"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=None
    ):
        await store_command(update, ctx)
    assert "don't have" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_mood_booster_happy_path():
    update, ctx = _make_update(args=["use", "mood_booster"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.store.db.consume_purchase") as mock_consume, patch(
        "handlers.store.db.set_mood_booster"
    ) as mock_set:
        await store_command(update, ctx)
    mock_consume.assert_called_once_with(1)
    mock_set.assert_called_once_with(1, True)
    assert "booster" in update.message.reply_text.call_args[0][0].lower()


# ── /store use catch_net ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_use_catch_net_not_in_bag():
    update, ctx = _make_update(args=["use", "catch_net"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=None
    ):
        await store_command(update, ctx)
    assert "don't have" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_catch_net_happy_path():
    update, ctx = _make_update(args=["use", "catch_net"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.store.db.consume_purchase") as mock_consume, patch(
        "handlers.store.db.set_catch_net"
    ) as mock_set:
        await store_command(update, ctx)
    mock_consume.assert_called_once_with(1)
    mock_set.assert_called_once_with(1, True)
    assert "catch net" in update.message.reply_text.call_args[0][0].lower()


# ── /store use breed_accelerator ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_use_breed_accelerator_not_in_bag():
    update, ctx = _make_update(args=["use", "breed_accelerator"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=None
    ):
        await store_command(update, ctx)
    assert "don't have" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_breed_accelerator_no_active_breed():
    update, ctx = _make_update(args=["use", "breed_accelerator"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch("handlers.store.db.get_pending_breed", return_value=None):
        await store_command(update, ctx)
    assert "no active breed" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_use_breed_accelerator_happy_path():
    update, ctx = _make_update(args=["use", "breed_accelerator"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_oldest_purchase", return_value=_purchase_row()
    ), patch(
        "handlers.store.db.get_pending_breed", return_value=_breed_row(hours_from_now=4)
    ), patch(
        "handlers.store.db.adjust_breed_time_and_consume"
    ) as mock_adjust:
        await store_command(update, ctx)
    mock_adjust.assert_called_once()
    assert "accelerator" in update.message.reply_text.call_args[0][0].lower()


# ── store_callback ────────────────────────────────────────────────────────────


def _make_callback(data):
    query = MagicMock()
    query.from_user.id = 1
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    query.message.reply_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query, MagicMock()


@pytest.mark.asyncio
async def test_callback_no_user():
    update, query, ctx = _make_callback("store_buy_mega_feed")
    with patch("handlers.store.db.get_user", return_value=None):
        await store_callback(update, ctx)
    query.answer.assert_called_once()
    assert "start" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_unknown_item():
    update, query, ctx = _make_callback("store_buy_dragon_egg")
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_callback(update, ctx)
    query.answer.assert_called_once()
    assert "unknown" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_insufficient_coins():
    update, query, ctx = _make_callback("store_buy_mega_feed")
    with patch("handlers.store.db.get_user", return_value=_make_user(coins=5)):
        await store_callback(update, ctx)
    query.answer.assert_called_once()
    assert "coins" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_buy_consumable_goes_to_bag():
    update, query, ctx = _make_callback("store_buy_mega_feed")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.deduct_coins"
    ) as mock_deduct, patch("handlers.store.db.record_purchase") as mock_record, patch(
        "handlers.store.check_achievements", new_callable=AsyncMock
    ):
        await store_callback(update, ctx)
    mock_deduct.assert_called_once_with(1, 30)
    mock_record.assert_called_once_with(1, "mega_feed")
    query.answer.assert_called_once()
    assert "bag" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_buy_cosmetic_not_owned():
    update, query, ctx = _make_callback("store_buy_title_keeper")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=False
    ), patch("handlers.store.db.deduct_coins") as mock_deduct, patch(
        "handlers.store.db.record_purchase"
    ) as mock_record, patch(
        "handlers.store.db.get_owned_title_keys", return_value={"title_keeper"}
    ), patch(
        "handlers.store.db.get_consumable_counts", return_value={}
    ):
        await store_callback(update, ctx)
    mock_deduct.assert_called_once()
    mock_record.assert_called_once_with(1, "title_keeper")
    assert "purchased" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_buy_cosmetic_already_owned():
    update, query, ctx = _make_callback("store_buy_title_keeper")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=True
    ):
        await store_callback(update, ctx)
    query.answer.assert_called_once()
    assert "already own" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_equip_title():
    update, query, ctx = _make_callback("store_equip_title_keeper")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=True
    ), patch("handlers.store.db.set_active_title") as mock_set:
        await store_callback(update, ctx)
    mock_set.assert_called_once_with(1, "title_keeper")
