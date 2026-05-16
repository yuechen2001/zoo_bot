import datetime
import db
from keyboards import mood_keyboard


async def tick(ctx):
    """Runs every 30 minutes. Sends mood prompts, decays stats, checks breeding."""
    await _send_mood_prompts(ctx)
    await _decay_stats()
    await _check_starved_animals(ctx)
    await _check_breed_completions(ctx)


async def _send_mood_prompts(ctx):
    users = db.get_all_active_users()
    if not users:
        return

    now_str = datetime.datetime.utcnow().isoformat()

    from collections import defaultdict
    by_group = defaultdict(list)
    for u in users:
        by_group[u["group_chat_id"]].append(u)

    for group_chat_id, members in by_group.items():
        for user in members:
            tg_id = user["user_id"]
            if user["last_prompt_at"] and (
                not user["last_checkin_at"] or user["last_checkin_at"] < user["last_prompt_at"]
            ):
                new_misses = (user["consecutive_misses"] or 0) + 1
                if new_misses >= 2:
                    with db.get_conn() as conn:
                        conn.execute(
                            "UPDATE users SET consecutive_misses = 0, streak_windows = 0 WHERE user_id = ?",
                            (tg_id,),
                        )
                    try:
                        await ctx.bot.send_message(
                            group_chat_id,
                            "💔 You missed 2 check-ins in a row — streak reset to 0!",
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
                group_chat_id,
                "🕐 *Mood check-in!* How are you feeling right now?",
                parse_mode="Markdown",
                reply_markup=mood_keyboard(),
            )
            with db.get_conn() as conn:
                conn.executemany(
                    "UPDATE users SET last_prompt_at = ? WHERE user_id = ?",
                    [(now_str, u["user_id"]) for u in members],
                )
        except Exception:
            pass


async def _decay_stats():
    users = db.get_all_users_with_animals()
    for user in users:
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE animals SET "
                "hunger = MAX(0, hunger - (SELECT hunger_decay FROM species WHERE species_id = animals.species_id)) "
                "WHERE user_id = ? AND is_breeding = 0",
                (user["user_id"],),
            )


async def _check_starved_animals(ctx):
    with db.get_conn() as conn:
        starved = conn.execute(
            "SELECT a.animal_id, a.user_id, a.nickname, s.name, s.emoji, u.group_chat_id "
            "FROM animals a "
            "JOIN species s ON s.species_id = a.species_id "
            "JOIN users u ON u.user_id = a.user_id "
            "WHERE a.hunger = 0 AND a.is_breeding = 0"
        ).fetchall()

    for animal in starved:
        name = animal["nickname"] or animal["name"]
        chat_id = animal["group_chat_id"] or animal["user_id"]
        try:
            await ctx.bot.send_message(
                chat_id,
                f"💔 *{animal['emoji']} {name}* ran away — they were too hungry!",
                parse_mode="Markdown",
            )
        except Exception:
            pass
        with db.get_conn() as conn:
            conn.execute("DELETE FROM animals WHERE animal_id = ?", (animal["animal_id"],))


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
