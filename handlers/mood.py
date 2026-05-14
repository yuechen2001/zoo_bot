import datetime
import re
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.mood_engine import calc_coins, EMOJI_LABELS, EMOJI_HAPPINESS_DELTA
from config import CHECKIN_WINDOW_MINUTES


async def moodstart_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET opted_in = 1 WHERE user_id = ?", (tg_id,))
    await update.message.reply_text("✅ Mood prompts enabled! You'll be pinged every 30 min.")


async def moodstop_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text("Use /start first!")
        return
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET opted_in = 0, streak_windows = 0, consecutive_misses = 0 WHERE user_id = ?",
            (tg_id,),
        )
    await update.message.reply_text("⏸ Mood prompts stopped. Streak reset.")


async def pause_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
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
    paused_until = (datetime.datetime.utcnow() + delta).isoformat()

    with db.get_conn() as conn:
        conn.execute("UPDATE users SET paused_until = ? WHERE user_id = ?", (paused_until, tg_id))

    label = f"{amount}{'h' if unit == 'h' else 'm'}"
    await update.message.reply_text(
        f"⏸ Paused for *{label}*. No prompts, streak frozen. Use /resume to end early.",
        parse_mode="Markdown",
    )


async def resume_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET paused_until = NULL WHERE user_id = ?", (tg_id,))
    await update.message.reply_text("▶️ Resumed! Mood prompts are back on.")


async def mood_checkin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    emoji = query.data[len("mood_"):]

    user = db.get_user(tg_id)
    if not user:
        await query.answer("Use /start first!")
        return

    # Enforce response window
    last_prompt = user["last_prompt_at"]
    if last_prompt:
        prompt_time = datetime.datetime.fromisoformat(last_prompt)
        elapsed_min = (datetime.datetime.utcnow() - prompt_time).total_seconds() / 60
        if elapsed_min > CHECKIN_WINDOW_MINUTES:
            await query.answer("Window closed!")
            await query.edit_message_text(
                f"⏰ Too late — the {CHECKIN_WINDOW_MINUTES}-min window closed.\n"
                f"Wait for the next prompt!"
            )
            return
    else:
        elapsed_min = 0

    # Prevent double-tapping same prompt
    last_checkin = user["last_checkin_at"]
    if last_checkin and last_prompt and last_checkin >= last_prompt:
        await query.answer("Already checked in for this prompt!")
        return

    # Update streak
    new_streak = user["streak_windows"] + 1
    coins = calc_coins(emoji, new_streak)
    now_str = datetime.datetime.utcnow().isoformat()

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET streak_windows = ?, consecutive_misses = 0, "
            "coins = coins + ?, last_checkin_at = ? WHERE user_id = ?",
            (new_streak, coins, now_str, tg_id),
        )
        conn.execute(
            "INSERT INTO mood_checkins (user_id, emoji, coins_earned, streak_window) VALUES (?, ?, ?, ?)",
            (tg_id, emoji, coins, new_streak),
        )
        # Apply mood to all non-breeding animals
        delta = EMOJI_HAPPINESS_DELTA.get(emoji, 0)
        if delta != 0:
            conn.execute(
                "UPDATE animals SET happiness = MAX(0, MIN(100, happiness + ?)) "
                "WHERE user_id = ? AND is_breeding = 0",
                (delta, tg_id),
            )

    label = EMOJI_LABELS.get(emoji, emoji)
    multiplier_note = ""
    if new_streak >= 4:
        from game.mood_engine import get_streak_multiplier
        mult = get_streak_multiplier(new_streak)
        multiplier_note = f" ({mult}x streak bonus)"

    await query.edit_message_text(
        f"{emoji} *{query.from_user.first_name}* — {label}\n\n"
        f"💰 +{coins} coins{multiplier_note}\n"
        f"🔥 Streak: {new_streak} windows",
        parse_mode="Markdown",
    )
    await query.answer(f"+{coins} coins!")


async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦁 *Zoo Bot — Commands*\n\n"
        "/start — join and get your starter animal\n"
        "/zoo — see your zoo\n"
        "/catch — search for a wild animal\n"
        "/feed <number> — feed an animal (10 🪙)\n"
        "/breed <a> <b> — breed two animals\n"
        "/breed collect — claim your offspring\n"
        "/name <number> <name> — nickname an animal\n\n"
        "*Mood prompts:*\n"
        "/moodstart — opt in to prompts\n"
        "/moodstop — opt out (resets streak)\n"
        "/pause 8h — freeze streak for a duration\n"
        "/resume — end pause early\n\n"
        "⏱ Respond within *15 min* of a prompt to earn coins!\n"
        "🔥 Longer streaks = coin multiplier (up to 3×)",
        parse_mode="Markdown",
    )
