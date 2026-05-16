"""
Admin / debug commands — only usable by IDs listed in ADMIN_IDS.

Usage:
  /admin help                        — list all commands
  /admin coins <amount>              — give yourself coins
  /admin givecoin <username> <amt>   — give coins to another user by username
  /admin give <species_name>         — add an animal directly to your zoo
  /admin hunger <number> <value>     — set animal #N hunger (0–100)
  /admin happiness <number> <value>  — set animal #N happiness (0–100)
  /admin tick                        — manually trigger the scheduler tick
  /admin prompt                      — send a mood prompt to yourself right now
  /admin reset                       — wipe your own data and start fresh
  /admin stats                       — show DB summary
"""

import uuid
from telegram import Update
from telegram.ext import ContextTypes

import db
from config import ADMIN_IDS


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def admin_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id

    if not _is_admin(tg_id):
        await update.message.reply_text("⛔ Not authorised.")
        return

    if not ctx.args:
        await update.message.reply_text(_help_text(), parse_mode="Markdown")
        return

    sub = ctx.args[0].lower()
    args = ctx.args[1:]

    if sub == "help":
        await update.message.reply_text(_help_text(), parse_mode="Markdown")

    elif sub == "coins":
        await _cmd_coins(update, tg_id, args)

    elif sub == "givecoin":
        await _cmd_givecoin(update, args)

    elif sub == "give":
        await _cmd_give(update, tg_id, args)

    elif sub == "hunger":
        await _cmd_set_stat(update, tg_id, args, "hunger")

    elif sub == "happiness":
        await _cmd_set_stat(update, tg_id, args, "happiness")

    elif sub == "tick":
        from scheduler import tick

        await tick(ctx)
        await update.message.reply_text("✅ Tick fired.")

    elif sub == "prompt":
        from keyboards import mood_keyboard

        now = __import__("datetime").datetime.utcnow().isoformat()
        with db.get_conn() as conn:
            conn.execute("UPDATE users SET last_prompt_at = ? WHERE user_id = ?", (now, tg_id))
        await update.message.reply_text(
            "🕐 *Mood check-in!* How are you feeling right now?",
            parse_mode="Markdown",
            reply_markup=mood_keyboard(),
        )

    elif sub == "reset":
        await _cmd_reset(update, tg_id)

    elif sub == "stats":
        await _cmd_stats(update)

    else:
        await update.message.reply_text(
            f"Unknown subcommand: `{sub}`\n\n{_help_text()}", parse_mode="Markdown"
        )


# ── Subcommands ───────────────────────────────────────────────────────────────


async def _cmd_coins(update, tg_id, args):
    if not args or not args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /admin coins <amount>")
        return
    amount = int(args[0])
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = MAX(0, coins + ?) WHERE user_id = ?", (amount, tg_id)
        )
    user = db.get_user(tg_id)
    sign = "+" if amount >= 0 else ""
    await update.message.reply_text(
        f"💰 {sign}{amount} coins. Balance: *{user['coins']}* 🪙", parse_mode="Markdown"
    )


async def _cmd_givecoin(update, args):
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /admin givecoin <username> <amount>")
        return
    username = args[0].lstrip("@")
    amount = int(args[1])
    target = db.get_user_by_username(username)
    if not target:
        await update.message.reply_text(f"User `{username}` not found.", parse_mode="Markdown")
        return
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = MAX(0, coins + ?) WHERE user_id = ?",
            (amount, target["user_id"]),
        )
    updated = db.get_user(target["user_id"])
    sign = "+" if amount >= 0 else ""
    await update.message.reply_text(
        f"💰 {sign}{amount} coins → *{username}*. Their balance: *{updated['coins']}* 🪙",
        parse_mode="Markdown",
    )


async def _cmd_give(update, tg_id, args):
    if not args:
        await update.message.reply_text("Usage: /admin give <species_name>")
        return
    name = " ".join(args).title()
    with db.get_conn() as conn:
        species = conn.execute(
            "SELECT * FROM species WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
    if not species:
        with db.get_conn() as conn:
            all_names = [
                r["name"] for r in conn.execute("SELECT name FROM species ORDER BY name").fetchall()
            ]
        await update.message.reply_text(
            f"Species `{name}` not found.\nAvailable: {', '.join(all_names)}",
            parse_mode="Markdown",
        )
        return
    animal_id = str(uuid.uuid4())
    db.add_animal(animal_id, tg_id, species["species_id"])
    await update.message.reply_text(
        f"✅ Added {species['emoji']} *{species['name']}* to your zoo!", parse_mode="Markdown"
    )


async def _cmd_set_stat(update, tg_id, args, stat):
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text(f"Usage: /admin {stat} <animal_number> <value 0-100>")
        return
    position = int(args[0])
    value = max(0, min(100, int(args[1])))
    animal = db.get_animal_by_position(tg_id, position)
    if not animal:
        await update.message.reply_text(f"No animal at position {position}.")
        return
    with db.get_conn() as conn:
        conn.execute(
            f"UPDATE animals SET {stat} = ? WHERE animal_id = ?", (value, animal["animal_id"])
        )
    name = animal["nickname"] or animal["species_name"]
    await update.message.reply_text(
        f"✅ {animal['emoji']} *{name}* {stat} set to {value}.", parse_mode="Markdown"
    )


async def _cmd_reset(update, tg_id):
    with db.get_conn() as conn:
        animal_ids = [
            r["animal_id"]
            for r in conn.execute(
                "SELECT animal_id FROM animals WHERE user_id = ?", (tg_id,)
            ).fetchall()
        ]
        if animal_ids:
            placeholders = ",".join("?" * len(animal_ids))
            conn.execute(
                f"DELETE FROM breeding_queue WHERE parent_a IN ({placeholders}) OR parent_b IN ({placeholders})",
                animal_ids + animal_ids,
            )
        conn.execute("DELETE FROM animals WHERE user_id = ?", (tg_id,))
        conn.execute("DELETE FROM mood_checkins WHERE user_id = ?", (tg_id,))
        conn.execute(
            "UPDATE users SET coins = 100, streak_windows = 0, consecutive_misses = 0, "
            "last_prompt_at = NULL, last_checkin_at = NULL, paused_until = NULL WHERE user_id = ?",
            (tg_id,),
        )
    await update.message.reply_text(
        "🔄 Your data has been reset. Use /start to get a new starter animal."
    )


async def _cmd_stats(update):
    with db.get_conn() as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        animals = conn.execute("SELECT COUNT(*) FROM animals").fetchone()[0]
        breeding = conn.execute(
            "SELECT COUNT(*) FROM breeding_queue WHERE collected = 0"
        ).fetchone()[0]
        checkins = conn.execute("SELECT COUNT(*) FROM mood_checkins").fetchone()[0]
        by_rarity = conn.execute(
            "SELECT s.rarity, COUNT(*) as n FROM animals a "
            "JOIN species s ON s.species_id = a.species_id GROUP BY s.rarity"
        ).fetchall()

    rarity_lines = "\n".join(f"  {r['rarity']}: {r['n']}" for r in by_rarity)
    await update.message.reply_text(
        f"📊 *DB Stats*\n\n"
        f"Users: {users}\n"
        f"Animals: {animals}\n"
        f"Active breeding: {breeding}\n"
        f"Total check-ins: {checkins}\n\n"
        f"*By rarity:*\n{rarity_lines}",
        parse_mode="Markdown",
    )


def _help_text() -> str:
    return (
        "🔧 *Admin Commands*\n\n"
        "`/admin coins <amount>` — add/remove your own coins\n"
        "`/admin givecoin <username> <amount>` — give coins to another user\n"
        "`/admin give <species>` — add animal to zoo\n"
        "`/admin hunger <#> <val>` — set animal hunger\n"
        "`/admin happiness <#> <val>` — set animal happiness\n"
        "`/admin tick` — fire the scheduler manually\n"
        "`/admin prompt` — send yourself a mood prompt now\n"
        "`/admin reset` — wipe your data and start fresh\n"
        "`/admin stats` — DB summary"
    )
