import pytest
from html.parser import HTMLParser
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.store import store_command, store_callback, store_tab_callback, _store_text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conftest import make_row


@pytest.fixture(autouse=True)
def no_achievements(monkeypatch):
    monkeypatch.setattr("game.achievements.check_achievements", AsyncMock())


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
        "username": "alice",
        "group_chat_id": -100,
        "coins": 500,
        "lucky_catch_active": 0,
        "mood_booster_active": 0,
        "catch_net_active": 0,
        "active_title": None,
    }
    return make_row(**{**defaults, **kw})


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


def test_store_text_html_no_badges():
    with patch("handlers.store.db.get_item_counts", return_value={}), patch(
        "handlers.store.db.get_user",
        return_value=_make_user(),
    ):
        _assert_html(_store_text(1))


def test_store_text_html_with_badges():
    counts = {key: 2 for key in ["lucky_token", "mood_booster", "catch_net", "mega_feed"]}
    with patch("handlers.store.db.get_item_counts", return_value=counts), patch(
        "handlers.store.db.get_user",
        return_value=_make_user(lucky_catch_active=1, mood_booster_active=1, catch_net_active=1),
    ):
        text = _store_text(1)
    _assert_html(text)
    assert "<i>" in text, "expected italic badge tags"


def test_store_text_references_inventory():
    with patch("handlers.store.db.get_item_counts", return_value={}), patch(
        "handlers.store.db.get_user", return_value=_make_user()
    ):
        text = _store_text(1)
    assert "/inventory" in text


# ── store_command display ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_shows_welcome_page_by_default():
    update, ctx = _make_update(args=[])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "Welcome" in reply
    # Items are behind tab buttons, not shown on the welcome page
    assert "Mega Feed" not in reply


@pytest.mark.asyncio
async def test_store_no_user():
    update, ctx = _make_update()
    with patch("handlers.store.db.get_user", return_value=None):
        await store_command(update, ctx)
    assert "start" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_store_unknown_subcommand_shows_welcome():
    update, ctx = _make_update(args=["xyz"])
    with patch("handlers.store.db.get_user", return_value=_make_user()):
        await store_command(update, ctx)
    assert "Welcome" in update.message.reply_text.call_args[0][0]


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
async def test_store_buy_item_records_purchase():
    update, ctx = _make_update(args=["buy", "lucky_token"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.deduct_coins"
    ) as mock_deduct, patch("handlers.store.db.record_purchase") as mock_record:
        await store_command(update, ctx)
    mock_deduct.assert_called_once_with(1, 80)
    mock_record.assert_called_once_with(1, "lucky_token")
    reply = update.message.reply_text.call_args[0][0]
    assert "Lucky Token" in reply
    assert "bag" in reply.lower()


@pytest.mark.asyncio
async def test_store_buy_item_points_to_inventory():
    update, ctx = _make_update(args=["buy", "lucky_token"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.deduct_coins"
    ), patch("handlers.store.db.record_purchase"):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "/inventory" in reply


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
    assert "/inventory" in reply


@pytest.mark.asyncio
async def test_store_buy_cosmetic_already_owned():
    update, ctx = _make_update(args=["buy", "title_keeper"])
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=True
    ):
        await store_command(update, ctx)
    reply = update.message.reply_text.call_args[0][0]
    assert "already own" in reply.lower() or "equip" in reply.lower()


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
async def test_callback_buy_item_goes_to_bag():
    update, query, ctx = _make_callback("store_buy_mega_feed")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.deduct_coins"
    ) as mock_deduct, patch("handlers.store.db.record_purchase") as mock_record, patch(
        "game.achievements.check_achievements", new_callable=AsyncMock
    ):
        await store_callback(update, ctx)
    mock_deduct.assert_called_once_with(1, 30)
    mock_record.assert_called_once_with(1, "mega_feed")
    query.answer.assert_called_once()
    assert "bag" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_callback_buy_item_points_to_inventory():
    update, query, ctx = _make_callback("store_buy_mega_feed")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.deduct_coins"
    ), patch("handlers.store.db.record_purchase"), patch(
        "game.achievements.check_achievements", new_callable=AsyncMock
    ):
        await store_callback(update, ctx)
    assert "/inventory" in query.answer.call_args[0][0]


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
        "handlers.store.db.get_item_counts", return_value={}
    ):
        await store_callback(update, ctx)
    mock_deduct.assert_called_once()
    mock_record.assert_called_once_with(1, "title_keeper")
    assert "purchased" in query.answer.call_args[0][0].lower()
    assert "/inventory" in query.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_callback_buy_cosmetic_already_owned():
    update, query, ctx = _make_callback("store_buy_title_keeper")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.has_purchased", return_value=True
    ):
        await store_callback(update, ctx)
    query.answer.assert_called_once()
    assert "already own" in query.answer.call_args[0][0].lower()


# ── store_tab_callback ────────────────────────────────────────────────────────


def _make_tab_callback(section: str):
    query = MagicMock()
    query.from_user.id = 1
    query.data = f"store_tab_{section}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query, MagicMock()


@pytest.mark.asyncio
async def test_store_tab_callback_no_user():
    update, query, ctx = _make_tab_callback("consumables")
    with patch("handlers.store.db.get_user", return_value=None):
        await store_tab_callback(update, ctx)
    query.answer.assert_called_once()
    assert "start" in query.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_store_tab_callback_items_edits_message():
    update, query, ctx = _make_tab_callback("items")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_owned_title_keys", return_value=set()
    ), patch("handlers.store.db.get_item_counts", return_value={}):
        await store_tab_callback(update, ctx)
    query.edit_message_text.assert_called_once()
    query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_store_tab_callback_titles_edits_message():
    update, query, ctx = _make_tab_callback("titles")
    with patch("handlers.store.db.get_user", return_value=_make_user()), patch(
        "handlers.store.db.get_owned_title_keys", return_value=set()
    ), patch("handlers.store.db.get_item_counts", return_value={}):
        await store_tab_callback(update, ctx)
    query.edit_message_text.assert_called_once()
