import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from config import INVESTMENT_HOURS, INVESTMENT_RETURN_RATE

MIN_INVEST = 10


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
        await update.message.reply_text(
            "💰 *Investment Bank*\n\n"
            f"Deposit coins and earn *{int(INVESTMENT_RETURN_RATE * 100)}% return* after {INVESTMENT_HOURS}h.\n\n"
            "Commands:\n"
            "`/invest <amount>` — deposit coins\n"
            "`/invest collect` — collect when ready\n\n"
            "Check investment status anytime with /zoo.",
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
            "You already have an active investment. Check status with /zoo.",
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

    invested_at = datetime.datetime.fromisoformat(inv["invested_at"])
    ready_at = invested_at + datetime.timedelta(hours=INVESTMENT_HOURS)
    if datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) < ready_at:
        remaining = ready_at - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        hours, rem = divmod(int(remaining.total_seconds()), 3600)
        minutes = rem // 60
        time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        await update.message.reply_text(
            f"⏳ Not ready yet! Come back in *{time_str}*.", parse_mode="Markdown"
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
