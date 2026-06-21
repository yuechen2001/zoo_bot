import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scheduler import _autofeed


def _make_ctx(send_side_effect=None):
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock(side_effect=send_side_effect)
    return ctx


def _make_user(
    uid=1, group_chat_id=-100, coins=200, threshold=50, max_coins=100, username="tester"
):
    user = MagicMock()
    user.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "user_id": uid,
            "group_chat_id": group_chat_id,
            "coins": coins,
            "autofeed_threshold": threshold,
            "autofeed_max_coins": max_coins,
            "username": username,
        }[k]
    )
    return user


def _make_animal(
    animal_id="a1",
    hunger=30,
    rarity="common",
    is_breeding=0,
    nickname=None,
    species_name="Mouse",
    emoji="🐭",
):
    a = MagicMock()
    a.__getitem__ = MagicMock(
        side_effect=lambda k: {
            "animal_id": animal_id,
            "hunger": hunger,
            "rarity": rarity,
            "is_breeding": is_breeding,
            "nickname": nickname,
            "species_name": species_name,
            "emoji": emoji,
        }[k]
    )
    return a


def _make_conn_mock():
    inner = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=inner)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_autofeed_feeds_hungry_animals():
    ctx = _make_ctx()
    user = _make_user(coins=200, threshold=50, max_coins=100)
    animal = _make_animal(hunger=30, rarity="common")  # cost 5

    with patch("scheduler.db.get_autofeed_users", return_value=[user]), patch(
        "scheduler.db.get_animals_below_hunger", return_value=[animal]
    ), patch("scheduler.db.get_user", return_value={"coins": 200}), patch(
        "scheduler.db.get_conn", return_value=_make_conn_mock()
    ):
        await _autofeed(ctx)

    ctx.bot.send_message.assert_called_once()
    msg = ctx.bot.send_message.call_args[0][1]
    assert "Auto-feed" in msg
    assert "5" in msg  # spent


@pytest.mark.asyncio
async def test_autofeed_no_animals_below_threshold_sends_nothing():
    ctx = _make_ctx()
    user = _make_user(coins=200)

    with patch("scheduler.db.get_autofeed_users", return_value=[user]), patch(
        "scheduler.db.get_animals_below_hunger", return_value=[]
    ):
        await _autofeed(ctx)

    ctx.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_autofeed_skips_when_no_coins():
    ctx = _make_ctx()
    user = _make_user(coins=0, threshold=50, max_coins=100)
    animal = _make_animal(hunger=30, rarity="common")  # cost 10

    with patch("scheduler.db.get_autofeed_users", return_value=[user]), patch(
        "scheduler.db.get_animals_below_hunger", return_value=[animal]
    ), patch("scheduler.db.get_user", return_value={"coins": 0}):
        await _autofeed(ctx)

    ctx.bot.send_message.assert_called_once()
    msg = ctx.bot.send_message.call_args[0][1]
    assert "skipped" in msg.lower()


@pytest.mark.asyncio
async def test_autofeed_respects_max_coins_cap():
    """With max_coins=8 and cost 5 per animal, only 1 of 2 animals should be fed."""
    ctx = _make_ctx()
    user = _make_user(coins=200, threshold=50, max_coins=8)
    animals = [
        _make_animal(animal_id="a1", hunger=10, rarity="common"),  # cost 5
        _make_animal(animal_id="a2", hunger=20, rarity="common"),  # cost 5 → exceeds remaining 3
    ]

    with patch("scheduler.db.get_autofeed_users", return_value=[user]), patch(
        "scheduler.db.get_animals_below_hunger", return_value=animals
    ), patch("scheduler.db.get_user", return_value={"coins": 200}), patch(
        "scheduler.db.get_conn", return_value=_make_conn_mock()
    ):
        await _autofeed(ctx)

    msg = ctx.bot.send_message.call_args[0][1]
    assert "Auto-feed" in msg
    assert "5" in msg  # spent only 5, not 10


@pytest.mark.asyncio
async def test_autofeed_plural_message():
    ctx = _make_ctx()
    user = _make_user(coins=200, threshold=50, max_coins=100)
    animals = [
        _make_animal(animal_id="a1", hunger=10, rarity="common"),
        _make_animal(animal_id="a2", hunger=20, rarity="common"),
    ]

    with patch("scheduler.db.get_autofeed_users", return_value=[user]), patch(
        "scheduler.db.get_animals_below_hunger", return_value=animals
    ), patch("scheduler.db.get_user", return_value={"coins": 200}), patch(
        "scheduler.db.get_conn", return_value=_make_conn_mock()
    ):
        await _autofeed(ctx)

    msg = ctx.bot.send_message.call_args[0][1]
    assert "Auto-feed" in msg


@pytest.mark.asyncio
async def test_autofeed_send_failure_does_not_raise():
    """A Telegram send error must not crash the tick."""
    ctx = _make_ctx(send_side_effect=Exception("Telegram error"))
    user = _make_user(coins=200)
    animal = _make_animal(hunger=30, rarity="common")

    with patch("scheduler.db.get_autofeed_users", return_value=[user]), patch(
        "scheduler.db.get_animals_below_hunger", return_value=[animal]
    ), patch("scheduler.db.get_user", return_value={"coins": 200}), patch(
        "scheduler.db.get_conn", return_value=_make_conn_mock()
    ):
        await _autofeed(ctx)  # should not raise


@pytest.mark.asyncio
async def test_autofeed_balance_shown_correctly():
    ctx = _make_ctx()
    user = _make_user(coins=150, threshold=50, max_coins=100)
    animal = _make_animal(hunger=30, rarity="common")  # cost 5

    with patch("scheduler.db.get_autofeed_users", return_value=[user]), patch(
        "scheduler.db.get_animals_below_hunger", return_value=[animal]
    ), patch("scheduler.db.get_user", return_value={"coins": 150}), patch(
        "scheduler.db.get_conn", return_value=_make_conn_mock()
    ):
        await _autofeed(ctx)

    msg = ctx.bot.send_message.call_args[0][1]
    assert "145" in msg  # 150 - 5 = 145 remaining
