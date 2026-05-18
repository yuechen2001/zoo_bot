import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from config import INVESTMENT_HOURS, INVESTMENT_RETURN_RATE
from game.constants import MIN_INVEST
from keyboards import invest_keyboard


def _is_ready(inv) -> bool:
    invested_at = datetime.datetime.fromisoformat(inv["invested_at"])
    ready_at = invested_at + datetime.timedelta(hours=INVESTMENT_HOURS)
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) >= ready_at


def _countdown_str(inv) -> str:
    invested_at = datetime.datetime.fromisoformat(inv["invested_at"])
    ready_at = invested_at + datetime.timedelta(hours=INVESTMENT_HOURS)
    remaining = ready_at - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    hours, rem = divmod(int(remaining.total_seconds()), 3600)
    minutes = rem // 60
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def _status_text(user, inv) -> str:
    rate_pct = int(INVESTMENT_RETURN_RATE * 100)
    if not inv:
        return (
            "💰 *Investment Bank*\n\n"
            f"Deposit coins and earn *{rate_pct}% return* after {INVESTMENT_HOURS}h.\n\n"
            f"Your balance: *{user['coins']}* 🪙"
        )
    if _is_ready(inv):
        profit = inv["return_amount"] - inv["amount"]
        return (
            f"✅ *Ready to collect!*\n\n"
            f"Invested: *{inv['amount']}* 🪙\n"
            f"Return: *{inv['return_amount']}* 🪙 (*+{profit}* 🪙)"
        )
    return (
        f"📈 *Investment in progress*\n\n"
        f"Invested: *{inv['amount']}* 🪙\n"
        f"Return: *{inv['return_amount']}* 🪙\n"
        f"⏳ Ready in: *{_countdown_str(inv)}*"
    )


async def invest_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    args = ctx.args or []
    subcommand = args[0].lower() if args else ""

    if subcommand == "collect":
        await _collect(update, tg_id, user)
    elif subcommand.isdigit() or (len(args) == 1 and args[0].lstrip("-").isdigit()):
        await _invest(update, tg_id, user, args[0])
    else:
        inv = db.get_active_investment(tg_id)
        ready = _is_ready(inv) if inv else False
        kb = invest_keyboard(user["coins"], inv is not None, ready)
        await update.message.reply_text(
            _status_text(user, inv),
            reply_markup=kb,
            parse_mode="Markdown",
        )


async def _invest(update, tg_id, user, amount_str):
    try:
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text("Amount must be a whole number.")
        return

    if amount < MIN_INVEST:
        await update.message.reply_text(f"Minimum investment is {MIN_INVEST} 🪙.")
        return

    if user["coins"] < amount:
        await update.message.reply_text(f"Not enough coins! You have {user['coins']} 🪙.")
        return

    existing = db.get_active_investment(tg_id)
    if existing:
        await update.message.reply_text(
            "You already have an active investment. Check status with /invest.",
            parse_mode="Markdown",
        )
        return

    return_amount = round(amount * (1 + INVESTMENT_RETURN_RATE))
    db.create_investment(tg_id, amount, return_amount)
    db.add_coins(tg_id, -amount)

    await update.message.reply_text(
        f"📈 Invested *{amount}* 🪙!\n\n"
        f"Return: *{return_amount}* 🪙 (+{int(INVESTMENT_RETURN_RATE * 100)}%)\n"
        f"Ready in: *{INVESTMENT_HOURS}h*\n\n"
        f"Use `/invest collect` when the time is up!",
        parse_mode="Markdown",
    )


async def _collect(update, tg_id, user):
    inv = db.get_active_investment(tg_id)
    if not inv:
        await update.message.reply_text(
            "No active investment. Use `/invest <amount>` to start one.",
            parse_mode="Markdown",
        )
        return

    if not _is_ready(inv):
        await update.message.reply_text(
            f"⏳ Not ready yet! Come back in *{_countdown_str(inv)}*.", parse_mode="Markdown"
        )
        return

    db.collect_investment(inv["id"])
    db.add_coins(tg_id, inv["return_amount"])

    profit = inv["return_amount"] - inv["amount"]
    await update.message.reply_text(
        f"💰 Investment collected!\n\n"
        f"You received *{inv['return_amount']}* 🪙\n"
        f"Profit: *+{profit}* 🪙",
        parse_mode="Markdown",
    )


async def invest_deposit_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    amount = int(query.data.removeprefix("invest_deposit_"))

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    if db.get_active_investment(tg_id):
        await query.answer("Already have an active investment!", show_alert=True)
        return

    if user["coins"] < amount:
        await query.answer(f"Not enough coins! You have {user['coins']} 🪙.", show_alert=True)
        return

    if amount < MIN_INVEST:
        await query.answer(f"Minimum investment is {MIN_INVEST} 🪙.", show_alert=True)
        return

    return_amount = round(amount * (1 + INVESTMENT_RETURN_RATE))
    db.create_investment(tg_id, amount, return_amount)
    db.add_coins(tg_id, -amount)

    user = db.get_user(tg_id)
    inv = db.get_active_investment(tg_id)
    kb = invest_keyboard(user["coins"], True, False)
    await query.answer()
    await query.edit_message_text(
        _status_text(user, inv),
        reply_markup=kb,
        parse_mode="Markdown",
    )


async def invest_max_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!", show_alert=True)
        return

    if db.get_active_investment(tg_id):
        await query.answer("Already have an active investment!", show_alert=True)
        return

    amount = user["coins"]
    if amount < MIN_INVEST:
        await query.answer(f"Need at least {MIN_INVEST} 🪙 to invest.", show_alert=True)
        return

    return_amount = round(amount * (1 + INVESTMENT_RETURN_RATE))
    db.create_investment(tg_id, amount, return_amount)
    db.add_coins(tg_id, -amount)

    user = db.get_user(tg_id)
    inv = db.get_active_investment(tg_id)
    kb = invest_keyboard(user["coins"], True, False)
    await query.answer()
    await query.edit_message_text(
        _status_text(user, inv),
        reply_markup=kb,
        parse_mode="Markdown",
    )


async def invest_collect_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id

    user = db.get_user(tg_id)
    inv = db.get_active_investment(tg_id)

    if not inv:
        await query.answer("No active investment.", show_alert=True)
        return

    if not _is_ready(inv):
        await query.answer(f"Not ready yet! Come back in {_countdown_str(inv)}.", show_alert=True)
        return

    db.collect_investment(inv["id"])
    db.add_coins(tg_id, inv["return_amount"])
    profit = inv["return_amount"] - inv["amount"]

    user = db.get_user(tg_id)
    kb = invest_keyboard(user["coins"], False, False)
    await query.answer()
    await query.edit_message_text(
        f"💰 *Investment collected!*\n\n"
        f"You received *{inv['return_amount']}* 🪙\n"
        f"Profit: *+{profit}* 🪙\n\n" + _status_text(user, None),
        reply_markup=kb,
        parse_mode="Markdown",
    )
