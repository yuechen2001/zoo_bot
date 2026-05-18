import datetime
import re
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.mood_engine import calc_coins, EMOJI_LABELS
from config import CHECKIN_WINDOW_MINUTES, ADMIN_IDS
from game.achievements import check_achievements


async def moodstart_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return
    db.set_opted_in(tg_id)
    await update.message.reply_text("✅ Mood prompts enabled! You'll be pinged every 30 min.")


async def moodstop_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return
    db.set_opted_out(tg_id)
    await update.message.reply_text(
        "⏸ Mood prompts stopped. Resume with /moodstart — your streak is preserved."
    )


async def pause_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if tg_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admins can use /pause.")
        return

    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return

    if not ctx.args:
        await update.message.reply_text("Usage: /pause 8h  or  /pause 30m")
        return

    duration_str = ctx.args[0].lower()
    match = re.fullmatch(r"(\d+)([hm])", duration_str)
    if not match:
        await update.message.reply_text("Format: /pause 8h  or  /pause 30m")
        return

    amount, unit = int(match.group(1)), match.group(2)
    delta = datetime.timedelta(hours=amount) if unit == "h" else datetime.timedelta(minutes=amount)
    paused_until = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + delta
    ).isoformat()

    db.set_paused_until(tg_id, paused_until)
    label = f"{amount}{'h' if unit == 'h' else 'm'}"
    await update.message.reply_text(
        f"⏸ Paused for *{label}*. No prompts, streak frozen. Use /resume to end early.",
        parse_mode="Markdown",
    )


async def resume_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if tg_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admins can use /resume.")
        return
    db.set_paused_until(tg_id, None)
    await update.message.reply_text("▶️ Resumed! Mood prompts are back on.")


async def mood_checkin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # data format: mood_{emoji}
    emoji = query.data.split("_", 1)[1]

    tg_id = query.from_user.id
    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first to join!", show_alert=True)
        return

    if not user["opted_in"]:
        await query.answer("Use /moodstart to opt in to prompts first!", show_alert=True)
        return

    # Sync group_chat_id from the message so users who never ran /start in
    # this group still get counted correctly in all_group_members_checked_in
    msg_chat_id = query.message.chat_id
    if query.message.chat.type in ("group", "supergroup") and user["group_chat_id"] != msg_chat_id:
        db.update_group_chat_id(tg_id, msg_chat_id)
        user = db.get_user(tg_id)

    # Enforce response window
    last_prompt = user["last_prompt_at"]
    if last_prompt:
        prompt_time = datetime.datetime.fromisoformat(last_prompt)
        elapsed_min = (
            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - prompt_time
        ).total_seconds() / 60
        if elapsed_min > CHECKIN_WINDOW_MINUTES:
            await query.answer("⏰ Window closed — wait for the next prompt!", show_alert=True)
            return
    else:
        elapsed_min = 0

    # Block duplicate responses via the prompt_responses table (atomic INSERT OR IGNORE)
    if not db.record_prompt_response(user["group_chat_id"] or 0, last_prompt, tg_id):
        await query.answer("Already checked in for this prompt!")
        return

    # Update streak
    new_streak = user["streak_windows"] + 1
    coins = calc_coins(emoji, new_streak)
    if user["mood_booster_active"]:
        coins *= 2
        db.set_mood_booster(tg_id, False)
    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    db.record_checkin(tg_id, emoji, coins, new_streak, now_str)

    label = EMOJI_LABELS.get(emoji, emoji)
    multiplier_note = ""
    if new_streak >= 4:
        from game.mood_engine import get_streak_multiplier

        mult = get_streak_multiplier(new_streak)
        multiplier_note = f" ({mult}x streak bonus)"

    # Respond with a private popup — keep the group message keyboard intact for others
    await query.answer(
        f"{emoji} {label} — +{coins} coins!{multiplier_note}\n🔥 Streak: {new_streak}",
        show_alert=True,
    )

    # Collapse the prompt once everyone in the group has responded
    if (
        user["group_chat_id"]
        and last_prompt
        and db.all_group_members_checked_in(user["group_chat_id"], last_prompt)
    ):
        try:
            await query.edit_message_text(
                "✅ *Everyone checked in!* See you next round.",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    await check_achievements(tg_id, "checkin", ctx)


_HELP_SECTIONS = {
    "zoo": (
        "🦁 *Zoo Bot — Your Zoo*\n\n"
        "/start — join and get your starter animal\n"
        "/zoo — view your zoo (one habitat per page, tap ◀ ▶ to browse)\n"
        "/catch — search for a wild animal (requires a lure from /store)\n"
        "/feed <numbers> — feed animal(s) (cost varies by rarity)\n"
        "/name <number> <name> — nickname an animal\n"
        "/sell <number> — sell an animal for coins\n"
        "/gift <number> @user — give an animal to another player\n"
        "/autofeed <threshold> <max\\_coins> — auto-feed below hunger level each tick\n"
        "/autofeed off — disable auto-feed\n"
        "/directory — browse all species & see which you own\n"
        "/achievements — view your milestones\n"
        "/footmassage — halve animal hunger decay for 1h (25 🪙, 4h cooldown)\n"
        "/enclosures — view and upgrade your habitat enclosures\n"
        "/enclosures collect — claim your pending enclosure income"
    ),
    "breeding": (
        "🥚 *Zoo Bot — Breeding*\n\n"
        "/breed <a> <b> — breed two animals together\n"
        "/breed collect — claim your finished offspring (enclosure must have space)\n"
        "/breed status — check time remaining on active breed\n\n"
        "💡 Same-habitat pairs get a breed time bonus from enclosure upgrades.\n"
        "💡 Well-fed animals breed faster."
    ),
    "store": (
        "🏪 *Zoo Bot — Store & Inventory*\n\n"
        "/store — browse items, lures, and cosmetic titles\n"
        "/store buy <item> — purchase an item directly\n"
        "/inventory — view your bag and owned titles\n"
        "/inventory use <item> — activate an item\n"
        "/inventory equip <title> — set your zoo title\n\n"
        "💡 Each habitat has its own lure — habitat lures give 1.5× catch rate."
    ),
    "coins": (
        "🪙 *Zoo Bot — Earning Coins*\n\n"
        "/daily — claim daily coins (50→75→100→150 on consecutive days)\n"
        "/trivia — animal trivia (+40 correct, +5 wrong, 4h cooldown)\n"
        "/gamble <amount> — coin flip bet (max 100 🪙)\n"
        "/slots — spin the slot machine (10 🪙 per spin)\n"
        "/trade @user <yours> <theirs> — offer an animal swap\n"
        "/invest <amount> — invest coins (25% return after 24h, shown in /zoo)\n"
        "/invest collect — collect your matured investment\n\n"
        "💡 Mood prompts earn coins too — see the Mood tab."
    ),
    "more": (
        "📋 *Zoo Bot — More*\n\n"
        "*Mood prompts:*\n"
        "/moodstart — opt in to prompts\n"
        "/moodstop — opt out (streak preserved)\n\n"
        "⏱ Respond within *15 min* of a prompt to earn coins!\n"
        "🔥 Longer streaks = coin multiplier (up to 3×)\n\n"
        "*Admin:*\n"
        "/admin help — full list of admin commands"
    ),
}


async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from keyboards import help_keyboard

    await update.message.reply_text(
        _HELP_SECTIONS["zoo"],
        parse_mode="Markdown",
        reply_markup=help_keyboard("zoo"),
    )


async def help_tab_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from keyboards import help_keyboard

    query = update.callback_query
    await query.answer()
    section = query.data.removeprefix("help_tab_")
    text = _HELP_SECTIONS.get(section, _HELP_SECTIONS["zoo"])
    try:
        await query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=help_keyboard(section)
        )
    except Exception:
        pass
