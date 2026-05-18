"""
Admin / debug commands — only usable by IDs listed in ADMIN_IDS.

Usage:
  /admin help                          — list all commands
  /admin coins <amount>                — add/remove your own coins (negative to remove)
  /admin givecoin <username> <amt>     — give coins to another user by username
  /admin reducecoin <username> <amt>   — reduce another user's coins by <amt> (positive number)
  /admin giveuser <username> <species> — add an animal to another user's zoo
  /admin listanimals <username>        — show all animals owned by a user
  /admin hunger <number> <value>       — set animal #N hunger (0–100)
  /admin pause <duration>              — freeze your streak (e.g. 8h or 30m)
  /admin resume                        — end pause early
  /admin tick                          — manually trigger the scheduler tick
  /admin prompt                        — send a mood prompt to yourself right now
  /admin reset                         — wipe your own data and start fresh
  /admin resetuser <username>          — wipe another user's data
  /admin stats                         — show DB summary
"""

import datetime
import re
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

    elif sub == "reducecoin":
        await _cmd_reducecoin(update, args)

    elif sub == "giveuser":
        await _cmd_giveuser(update, args)

    elif sub == "listanimals":
        await _cmd_listanimals(update, args)

    elif sub == "hunger":
        await _cmd_set_stat(update, tg_id, args, "hunger")

    elif sub == "pause":
        await _cmd_pause(update, tg_id, args)

    elif sub == "resume":
        await _cmd_resume(update, tg_id)

    elif sub == "tick":
        from scheduler import tick

        await tick(ctx)
        await update.message.reply_text("✅ Tick fired.")

    elif sub == "prompt":
        from keyboards import mood_keyboard

        now = __import__("datetime").datetime.utcnow().isoformat()
        db.set_last_prompt_at(tg_id, now)
        await update.message.reply_text(
            "🕐 *Mood check-in!* How are you feeling right now?",
            parse_mode="Markdown",
            reply_markup=mood_keyboard(),
        )

    elif sub == "reset":
        await _cmd_reset(update, tg_id)

    elif sub == "resetuser":
        await _cmd_resetuser(update, args)

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


async def _cmd_reducecoin(update, args):
    if len(args) < 2 or not args[1].isdigit():
        await update.message.reply_text("Usage: /admin reducecoin <username> <amount>")
        return
    username = args[0].lstrip("@")
    amount = int(args[1])
    target = db.get_user_by_username(username)
    if not target:
        await update.message.reply_text(f"User `{username}` not found.", parse_mode="Markdown")
        return
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET coins = MAX(0, coins - ?) WHERE user_id = ?",
            (amount, target["user_id"]),
        )
    updated = db.get_user(target["user_id"])
    await update.message.reply_text(
        f"💸 Removed *{amount}* 🪙 from *{username}*. Their balance: *{updated['coins']}* 🪙",
        parse_mode="Markdown",
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
    db.admin_set_animal_stat(animal["animal_id"], stat, value)
    name = animal["nickname"] or animal["species_name"]
    await update.message.reply_text(
        f"✅ {animal['emoji']} *{name}* {stat} set to {value}.", parse_mode="Markdown"
    )


async def _cmd_giveuser(update, args):
    if len(args) < 2:
        await update.message.reply_text("Usage: /admin giveuser <username> <species>")
        return
    username = args[0].lstrip("@")
    name = " ".join(args[1:]).title()
    target = db.get_user_by_username(username)
    if not target:
        await update.message.reply_text(f"User `{username}` not found.", parse_mode="Markdown")
        return
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
    db.add_animal(animal_id, target["user_id"], species["species_id"])
    await update.message.reply_text(
        f"✅ Added {species['emoji']} *{species['name']}* to *{username}*'s zoo!",
        parse_mode="Markdown",
    )


async def _cmd_listanimals(update, args):
    if not args:
        await update.message.reply_text("Usage: /admin listanimals <username>")
        return
    username = args[0].lstrip("@")
    target = db.get_user_by_username(username)
    if not target:
        await update.message.reply_text(f"User `{username}` not found.", parse_mode="Markdown")
        return
    animals = db.get_animals(target["user_id"])
    if not animals:
        await update.message.reply_text(f"*{username}* has no animals.", parse_mode="Markdown")
        return
    lines = [f"🐾 *{username}'s animals* ({len(animals)} total)\n"]
    for i, a in enumerate(animals, 1):
        name = a["nickname"] or a["species_name"]
        lock = " 🔒" if a["is_breeding"] else ""
        lines.append(f"#{i} {a['emoji']} {name} — 🍖 {a['hunger']} [{a['rarity']}]{lock}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _cmd_pause(update, tg_id, args):
    if not args:
        await update.message.reply_text("Usage: /admin pause 8h  or  /admin pause 30m")
        return
    match = re.fullmatch(r"(\d+)([hm])", args[0].lower())
    if not match:
        await update.message.reply_text("Format: /admin pause 8h  or  /admin pause 30m")
        return
    amount, unit = int(match.group(1)), match.group(2)
    delta = datetime.timedelta(hours=amount) if unit == "h" else datetime.timedelta(minutes=amount)
    paused_until = (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + delta
    ).isoformat()
    user = db.get_user(tg_id)
    group_chat_id = user["group_chat_id"]
    with db.get_conn() as conn:
        if group_chat_id:
            conn.execute(
                "UPDATE users SET paused_until = ? WHERE group_chat_id = ?",
                (paused_until, group_chat_id),
            )
        else:
            conn.execute(
                "UPDATE users SET paused_until = ? WHERE user_id = ?", (paused_until, tg_id)
            )
    label = f"{amount}{'h' if unit == 'h' else 'm'}"
    await update.message.reply_text(
        f"⏸ Paused for *{label}*. No prompts or streak changes for anyone in the group. Use /admin resume to end early.",
        parse_mode="Markdown",
    )


async def _cmd_resume(update, tg_id):
    user = db.get_user(tg_id)
    group_chat_id = user["group_chat_id"]
    with db.get_conn() as conn:
        if group_chat_id:
            conn.execute(
                "UPDATE users SET paused_until = NULL WHERE group_chat_id = ?", (group_chat_id,)
            )
        else:
            conn.execute("UPDATE users SET paused_until = NULL WHERE user_id = ?", (tg_id,))
    await update.message.reply_text("▶️ Resumed! Mood prompts are back on for everyone.")


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


async def _cmd_resetuser(update, args):
    if not args:
        await update.message.reply_text("Usage: /admin resetuser <username>")
        return
    username = args[0].lstrip("@")
    target = db.get_user_by_username(username)
    if not target:
        await update.message.reply_text(f"User `{username}` not found.", parse_mode="Markdown")
        return
    uid = target["user_id"]
    with db.get_conn() as conn:
        animal_ids = [
            r["animal_id"]
            for r in conn.execute(
                "SELECT animal_id FROM animals WHERE user_id = ?", (uid,)
            ).fetchall()
        ]
        if animal_ids:
            placeholders = ",".join("?" * len(animal_ids))
            conn.execute(
                f"DELETE FROM breeding_queue WHERE parent_a IN ({placeholders}) OR parent_b IN ({placeholders})",
                animal_ids + animal_ids,
            )
        conn.execute("DELETE FROM animals WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM mood_checkins WHERE user_id = ?", (uid,))
        conn.execute(
            "UPDATE users SET coins = 100, streak_windows = 0, consecutive_misses = 0, "
            "last_prompt_at = NULL, last_checkin_at = NULL, paused_until = NULL WHERE user_id = ?",
            (uid,),
        )
    await update.message.reply_text(
        f"🔄 *{username}*'s data has been reset.", parse_mode="Markdown"
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
        "`/admin coins <amount>` — add/remove your own coins (negative to remove)\n"
        "`/admin givecoin <username> <amount>` — give coins to another user\n"
        "`/admin reducecoin <username> <amount>` — remove coins from a user\n"
        "`/admin giveuser <username> <species>` — add animal to a user's zoo\n"
        "`/admin listanimals <username>` — show all animals owned by a user\n"
        "`/admin hunger <#> <val>` — set animal hunger (0–100)\n"
        "`/admin pause <duration>` — freeze streak (e.g. 8h or 30m)\n"
        "`/admin resume` — end pause early\n"
        "`/admin tick` — fire the scheduler manually\n"
        "`/admin prompt` — send yourself a mood prompt now\n"
        "`/admin reset` — wipe your own data and start fresh\n"
        "`/admin resetuser <username>` — wipe another user's data\n"
        "`/admin stats` — DB summary (users, animals, check-ins)"
    )
