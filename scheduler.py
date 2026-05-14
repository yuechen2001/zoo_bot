import datetime
import db
from keyboards import mood_keyboard


async def tick(ctx):
    """Runs every 30 minutes. Sends mood prompts, decays stats, checks breeding."""
    await _send_mood_prompts(ctx)
    await _decay_stats()
    await _check_breed_completions(ctx)


async def _send_mood_prompts(ctx):
    users = db.get_all_active_users()
    if not users:
        return

    now_str = datetime.datetime.utcnow().isoformat()

    for user in users:
        tg_id = user["user_id"]
        group_chat_id = user["group_chat_id"]

        # Track consecutive misses if user didn't respond to the last prompt
        if user["last_prompt_at"] and (
            not user["last_checkin_at"] or user["last_checkin_at"] < user["last_prompt_at"]
        ):
            new_misses = (user["consecutive_misses"] or 0) + 1
            if new_misses >= 2:
                # Reset streak
                with db.get_conn() as conn:
                    conn.execute(
                        "UPDATE users SET consecutive_misses = 0, streak_windows = 0 WHERE user_id = ?",
                        (tg_id,),
                    )
                try:
                    await ctx.bot.send_message(
                        group_chat_id or tg_id,
                        f"💔 You missed 2 check-ins in a row — streak reset to 0!",
                    )
                except Exception:
                    pass
            else:
                with db.get_conn() as conn:
                    conn.execute(
                        "UPDATE users SET consecutive_misses = ? WHERE user_id = ?",
                        (new_misses, tg_id),
                    )

        try:
            await ctx.bot.send_message(
                group_chat_id or tg_id,
                "🕐 *Mood check-in!* How are you feeling right now?",
                parse_mode="Markdown",
                reply_markup=mood_keyboard(),
            )
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE users SET last_prompt_at = ? WHERE user_id = ?",
                    (now_str, tg_id),
                )
        except Exception:
            pass


async def _decay_stats():
    users = db.get_all_users_with_animals()
    for user in users:
        with db.get_conn() as conn:
            # Decay hunger for all non-breeding animals using their species decay rate
            conn.execute(
                "UPDATE animals SET "
                "hunger = MAX(0, hunger - (SELECT hunger_decay FROM species WHERE species_id = animals.species_id)) "
                "WHERE user_id = ? AND is_breeding = 0",
                (user["user_id"],),
            )
            # If hunger < 30, also decay happiness
            conn.execute(
                "UPDATE animals SET happiness = MAX(0, happiness - 3) "
                "WHERE user_id = ? AND is_breeding = 0 AND hunger < 30",
                (user["user_id"],),
            )


async def _check_breed_completions(ctx):
    ready = db.get_ready_breeds()
    for breed in ready:
        group_chat_id = breed["group_chat_id"]
        if not group_chat_id:
            continue
        try:
            await ctx.bot.send_message(
                group_chat_id,
                f"🥚 *Breeding complete!*\n"
                f"{breed['emoji_a']} {breed['name_a']} × {breed['emoji_b']} {breed['name_b']} "
                f"→ {breed['emoji_offspring']} {breed['name_offspring']}\n\n"
                f"Use `/breed collect` to claim your new animal!",
                parse_mode="Markdown",
            )
        except Exception:
            pass
