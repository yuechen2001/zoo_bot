import uuid
import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from achievements import check_achievements
from game.breed_engine import (
    resolve_offspring,
    calc_breed_ready_at,
    calc_breed_cost,
    breed_duration_str,
)
from species_data import ENCLOSURE_LEVELS, HABITATS


async def breed_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = db.get_user(tg_id)

    if not user:
        await update.message.reply_text("Use /start first!")
        return

    # /breed collect
    if ctx.args and ctx.args[0].lower() == "collect":
        await _collect_breed(update, tg_id, ctx)
        return

    # /breed status
    if ctx.args and ctx.args[0].lower() == "status":
        await _breed_status(update, tg_id)
        return

    # /breed <a> <b>
    if not ctx.args or len(ctx.args) < 2 or not ctx.args[0].isdigit() or not ctx.args[1].isdigit():
        await update.message.reply_text(
            "Usage:\n"
            "`/breed 1 3` — breed animal #1 with animal #3\n"
            "`/breed status` — check time remaining\n"
            "`/breed collect` — claim your offspring",
            parse_mode="Markdown",
        )
        return

    pos_a, pos_b = int(ctx.args[0]), int(ctx.args[1])
    if pos_a == pos_b:
        await update.message.reply_text("Pick two different animals!")
        return

    animal_a = db.get_animal_by_position(tg_id, pos_a)
    animal_b = db.get_animal_by_position(tg_id, pos_b)

    if not animal_a or not animal_b:
        count = len(db.get_animals(tg_id))
        await update.message.reply_text(f"Invalid positions. You have {count} animal(s).")
        return

    if animal_a["is_breeding"] or animal_b["is_breeding"]:
        await update.message.reply_text("One of those animals is already breeding!")
        return

    pending = db.get_pending_breed(tg_id)
    if pending:
        await update.message.reply_text(
            "You already have a breeding in progress! Use `/breed collect` when it's ready.",
            parse_mode="Markdown",
        )
        return

    rarity_a = animal_a["rarity"]
    rarity_b = animal_b["rarity"]
    cost = calc_breed_cost(rarity_a, rarity_b)

    habitat_bonus = 0.0
    habitat_a = animal_a.get("habitat")
    habitat_b = animal_b.get("habitat")
    if habitat_a and habitat_a == habitat_b:
        enc_level = db.get_enclosure_level(tg_id, habitat_a)
        habitat_bonus = ENCLOSURE_LEVELS[enc_level]["breed_bonus"]

    duration = breed_duration_str(
        rarity_a, rarity_b, animal_a["hunger"], animal_b["hunger"], habitat_bonus
    )

    if user["coins"] < cost:
        await update.message.reply_text(
            f"Not enough coins! Breeding costs {cost} 🪙 (you have {user['coins']})."
        )
        return

    name_a = animal_a["nickname"] or animal_a["species_name"]
    name_b = animal_b["nickname"] or animal_b["species_name"]

    with db.get_conn() as conn:
        offspring_species_id = resolve_offspring(rarity_a, rarity_b, conn)
        ready_at = calc_breed_ready_at(
            rarity_a, rarity_b, animal_a["hunger"], animal_b["hunger"], habitat_bonus
        )
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, tg_id))
        conn.execute(
            "UPDATE animals SET is_breeding = 1 WHERE animal_id IN (?, ?)",
            (animal_a["animal_id"], animal_b["animal_id"]),
        )
        conn.execute(
            "INSERT INTO breeding_queue (user_id, parent_a, parent_b, offspring_species_id, ready_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (tg_id, animal_a["animal_id"], animal_b["animal_id"], offspring_species_id, ready_at),
        )

    bonus_line = ""
    if habitat_bonus > 0:
        h_info = HABITATS[habitat_a]
        bonus_line = (
            f"⚡ {h_info['emoji']} Habitat bonus: -{int(habitat_bonus * 100)}% breed time\n"
        )

    await update.message.reply_text(
        f"💕 *{animal_a['emoji']} {name_a}* × *{animal_b['emoji']} {name_b}* are now breeding!\n\n"
        f"Cost: -{cost} 🪙\n"
        f"{bonus_line}"
        f"Ready in: *{duration}*\n\n"
        f"Use `/breed collect` when the timer is up!",
        parse_mode="Markdown",
    )


async def _breed_status(update, tg_id):
    pending = db.get_pending_breed(tg_id)
    if not pending:
        await update.message.reply_text("No breeding in progress.")
        return

    with db.get_conn() as conn:
        pa = conn.execute(
            "SELECT a.nickname, s.name, s.emoji FROM animals a "
            "JOIN species s ON s.species_id = a.species_id WHERE a.animal_id = ?",
            (pending["parent_a"],),
        ).fetchone()
        pb = conn.execute(
            "SELECT a.nickname, s.name, s.emoji FROM animals a "
            "JOIN species s ON s.species_id = a.species_id WHERE a.animal_id = ?",
            (pending["parent_b"],),
        ).fetchone()

    name_a = pa["nickname"] or pa["name"] if pa else "?"
    name_b = pb["nickname"] or pb["name"] if pb else "?"
    emoji_a = pa["emoji"] if pa else ""
    emoji_b = pb["emoji"] if pb else ""

    ready_at = datetime.datetime.fromisoformat(pending["ready_at"])
    remaining = ready_at - datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    if remaining.total_seconds() <= 0:
        time_str = "ready! Use `/breed collect`"
    else:
        hours, rem = divmod(int(remaining.total_seconds()), 3600)
        minutes = rem // 60
        time_str = f"{hours}h {minutes}m remaining" if hours else f"{minutes}m remaining"

    await update.message.reply_text(
        f"💕 *{emoji_a} {name_a}* × *{emoji_b} {name_b}*\n⏳ {time_str}",
        parse_mode="Markdown",
    )


async def _collect_breed(update, tg_id, ctx=None):
    pending = db.get_pending_breed(tg_id)

    if not pending:
        await update.message.reply_text(
            "No breeding in progress! Use `/breed <a> <b>` to start one."
        )
        return

    ready_at = datetime.datetime.fromisoformat(pending["ready_at"])
    if datetime.datetime.now(datetime.UTC).replace(tzinfo=None) < ready_at:
        remaining = ready_at - datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        hours, rem = divmod(int(remaining.total_seconds()), 3600)
        minutes = rem // 60
        time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        await update.message.reply_text(
            f"⏳ Not ready yet! Come back in *{time_str}*.", parse_mode="Markdown"
        )
        return

    # Collect!
    offspring_species = db.get_species(pending["offspring_species_id"])
    animal_id = str(uuid.uuid4())

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO animals (animal_id, user_id, species_id) VALUES (?, ?, ?)",
            (animal_id, tg_id, pending["offspring_species_id"]),
        )
        conn.execute(
            "UPDATE animals SET is_breeding = 0 WHERE animal_id IN (?, ?)",
            (pending["parent_a"], pending["parent_b"]),
        )
        conn.execute("UPDATE breeding_queue SET collected = 1 WHERE id = ?", (pending["id"],))

    await update.message.reply_text(
        f"🥚✨ Your egg has hatched!\n\n"
        f"A *{offspring_species['emoji']} {offspring_species['name']}* joined your zoo!\n"
        f"Use `/name <number> <name>` to give it a nickname.",
        parse_mode="Markdown",
    )
    if ctx:
        await check_achievements(tg_id, "breed", ctx)


async def breed_collect_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _collect_breed(query, query.from_user.id, ctx)
