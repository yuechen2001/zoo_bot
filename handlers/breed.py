import random
import uuid
import datetime
from telegram import Update
from telegram.ext import ContextTypes
import db
from game.achievements import check_achievements
from game.breed_engine import (
    resolve_offspring,
    calc_breed_ready_at,
    calc_breed_cost,
    breed_duration_str,
)
from game.species_data import ENCLOSURE_LEVELS, HABITATS
from keyboards import animal_picker_keyboard


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

    # /breed <a> <b>
    if not ctx.args or len(ctx.args) < 2 or not ctx.args[0].isdigit() or not ctx.args[1].isdigit():
        pending = db.get_pending_breed(tg_id)
        if pending:
            await update.message.reply_text(
                "You already have a breeding in progress! Use `/breed collect` when it's ready.",
                parse_mode="Markdown",
            )
            return
        animals = db.get_animals(tg_id)
        breeding_ids = {a["animal_id"] for a in animals if a["is_breeding"]}
        available = [a for a in animals if a["animal_id"] not in breeding_ids]
        if len(available) < 2:
            await update.message.reply_text(
                "You need at least 2 available animals to breed.\n\n"
                "Use `/breed collect` to claim any in-progress offspring.",
                parse_mode="Markdown",
            )
            return
        kb = animal_picker_keyboard(
            animals,
            "breed_p1",
            "breed_cancel",
            disabled_ids=breeding_ids,
            page=0,
            page_callback_prefix="breed_page",
        )
        await update.message.reply_text("Choose the first parent:", reply_markup=kb)
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

    cost = calc_breed_cost(animal_a["rarity"], animal_b["rarity"])
    if user["coins"] < cost:
        await update.message.reply_text(
            f"Not enough coins! Breeding costs {cost} 🪙 (you have {user['coins']})."
        )
        return

    await update.message.reply_text(
        _breed_start(tg_id, animal_a, animal_b, cost), parse_mode="Markdown"
    )


def _breed_start(tg_id, animal_a, animal_b, cost) -> str:
    """Execute breed in DB and return the confirmation message text."""
    rarity_a, rarity_b = animal_a["rarity"], animal_b["rarity"]

    habitat_bonus = 0.0
    habitat_a, habitat_b = animal_a["habitat"], animal_b["habitat"]
    if habitat_a and habitat_a == habitat_b:
        enc_level = db.get_enclosure_level(tg_id, habitat_a)
        habitat_bonus = ENCLOSURE_LEVELS[enc_level]["breed_bonus"]

    duration = breed_duration_str(
        rarity_a, rarity_b, animal_a["hunger"], animal_b["hunger"], habitat_bonus
    )
    name_a = animal_a["nickname"] or animal_a["species_name"]
    name_b = animal_b["nickname"] or animal_b["species_name"]

    offspring_species_id = resolve_offspring(rarity_a, rarity_b, db.get_species_candidates)
    ready_at = calc_breed_ready_at(
        rarity_a, rarity_b, animal_a["hunger"], animal_b["hunger"], habitat_bonus
    )
    db.start_breed(
        tg_id, animal_a["animal_id"], animal_b["animal_id"], offspring_species_id, ready_at, cost
    )

    bonus_line = ""
    if habitat_bonus > 0:
        h_info = HABITATS[habitat_a]
        bonus_line = (
            f"⚡ {h_info['emoji']} Habitat bonus: -{int(habitat_bonus * 100)}% breed time\n"
        )

    return (
        f"💕 *{animal_a['emoji']} {name_a}* × *{animal_b['emoji']} {name_b}* are now breeding!\n\n"
        f"Cost: -{cost} 🪙\n"
        f"{bonus_line}"
        f"Ready in: *{duration}*\n\n"
        f"Use `/breed collect` when the timer is up!"
    )


async def _collect_breed(update, tg_id, ctx=None):
    pending = db.get_pending_breed(tg_id)

    if not pending:
        await update.message.reply_text(
            "No breeding in progress.\n\n" "Use `/breed 1 3` to breed animal #1 with animal #3.",
            parse_mode="Markdown",
        )
        return

    ready_at = datetime.datetime.fromisoformat(pending["ready_at"])
    if datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) < ready_at:
        remaining = ready_at - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        hours, rem = divmod(int(remaining.total_seconds()), 3600)
        minutes = rem // 60
        time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        await update.message.reply_text(
            f"⏳ Not ready yet! Come back in *{time_str}*.", parse_mode="Markdown"
        )
        return

    # Check enclosure capacity before adding offspring
    offspring_species = db.get_species(pending["offspring_species_id"])
    habitat = offspring_species["habitat"] or "woodland"
    enc_level = db.get_enclosure_level(tg_id, habitat)
    capacity = ENCLOSURE_LEVELS[enc_level]["capacity"]
    current = db.get_animal_count_by_habitat(tg_id, habitat)
    if current >= capacity:
        h_info = HABITATS.get(habitat, {"name": habitat.title(), "emoji": "🏕"})
        await update.message.reply_text(
            f"❌ Your *{h_info['emoji']} {h_info['name']}* enclosure is full "
            f"({current}/{capacity})!\n\n"
            f"Sell or gift an animal to make room, then use `/breed collect` again.",
            parse_mode="Markdown",
        )
        return

    animal_id = str(uuid.uuid4())
    db.collect_breed(
        tg_id,
        animal_id,
        pending["offspring_species_id"],
        pending["id"],
        pending["parent_a"],
        pending["parent_b"],
    )
    shiny = random.random() < 0.015
    if shiny:
        db.set_animal_shiny(animal_id)
    shiny_str = "⭐ " if shiny else ""

    await update.message.reply_text(
        f"🥚✨ Your egg has hatched!\n\n"
        f"A *{offspring_species['emoji']} {shiny_str}{offspring_species['name']}* joined your zoo!\n"
        f"Use `/name <number> <name>` to give it a nickname.",
        parse_mode="Markdown",
    )
    if ctx:
        await check_achievements(tg_id, "breed", ctx)


async def breed_collect_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _collect_breed(query, query.from_user.id, ctx)


async def breed_p1_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    pos1 = int(query.data.removeprefix("breed_p1_"))

    pending = db.get_pending_breed(tg_id)
    if pending:
        await query.answer("Already breeding! Use /breed collect.", show_alert=True)
        return

    animal_a = db.get_animal_by_position(tg_id, pos1)
    if not animal_a:
        await query.answer("That animal no longer exists.", show_alert=True)
        return
    if animal_a["is_breeding"]:
        await query.answer("That animal is already breeding.", show_alert=True)
        return

    name_a = animal_a["nickname"] or animal_a["species_name"]
    animals = db.get_animals(tg_id)
    breeding_ids = {a["animal_id"] for a in animals if a["is_breeding"]}
    disabled_ids = breeding_ids | {animal_a["animal_id"]}

    kb = animal_picker_keyboard(
        animals,
        f"breed_p2_{pos1}",
        "breed_cancel",
        disabled_ids=disabled_ids,
        page=0,
        page_callback_prefix=f"breed_p2_page_{pos1}",
    )
    await query.answer()
    await query.edit_message_text(
        f"🐾 *{animal_a['emoji']} {name_a}* chosen as parent 1\n\nChoose parent 2:",
        reply_markup=kb,
        parse_mode="Markdown",
    )


async def breed_p2_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    rest = query.data.removeprefix("breed_p2_")
    pos1_str, pos2_str = rest.split("_", 1)
    pos_a, pos_b = int(pos1_str), int(pos2_str)

    user = db.get_user(tg_id)
    animal_a = db.get_animal_by_position(tg_id, pos_a)
    animal_b = db.get_animal_by_position(tg_id, pos_b)

    if not animal_a or not animal_b:
        await query.answer("One of those animals no longer exists.", show_alert=True)
        return

    if animal_a["is_breeding"] or animal_b["is_breeding"]:
        await query.answer("One of those animals is already breeding!", show_alert=True)
        return

    pending = db.get_pending_breed(tg_id)
    if pending:
        await query.answer("Already breeding! Use /breed collect.", show_alert=True)
        return

    cost = calc_breed_cost(animal_a["rarity"], animal_b["rarity"])
    if user["coins"] < cost:
        await query.answer(
            f"Not enough coins! Breeding costs {cost} 🪙 (you have {user['coins']}).",
            show_alert=True,
        )
        return

    await query.answer()
    await query.edit_message_text(
        _breed_start(tg_id, animal_a, animal_b, cost), parse_mode="Markdown"
    )
    await check_achievements(tg_id, "breed", ctx)


async def breed_cancel_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Cancelled")
    await query.edit_message_text("Breed cancelled.")


async def breed_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    page = int(query.data.removeprefix("breed_page_"))

    pending = db.get_pending_breed(tg_id)
    if pending:
        await query.answer("Already breeding! Use /breed collect.", show_alert=True)
        return

    animals = db.get_animals(tg_id)
    breeding_ids = {a["animal_id"] for a in animals if a["is_breeding"]}
    kb = animal_picker_keyboard(
        animals,
        "breed_p1",
        "breed_cancel",
        disabled_ids=breeding_ids,
        page=page,
        page_callback_prefix="breed_page",
    )
    await query.answer()
    await query.edit_message_text("Choose the first parent:", reply_markup=kb)


async def breed_p2_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = query.from_user.id
    rest = query.data.removeprefix("breed_p2_page_")
    pos1_str, page_str = rest.rsplit("_", 1)
    pos1, page = int(pos1_str), int(page_str)

    animal_a = db.get_animal_by_position(tg_id, pos1)
    if not animal_a:
        await query.answer("That animal no longer exists.", show_alert=True)
        return

    animals = db.get_animals(tg_id)
    breeding_ids = {a["animal_id"] for a in animals if a["is_breeding"]}
    disabled_ids = breeding_ids | {animal_a["animal_id"]}
    name_a = animal_a["nickname"] or animal_a["species_name"]

    kb = animal_picker_keyboard(
        animals,
        f"breed_p2_{pos1}",
        "breed_cancel",
        disabled_ids=disabled_ids,
        page=page,
        page_callback_prefix=f"breed_p2_page_{pos1}",
    )
    await query.answer()
    await query.edit_message_text(
        f"🐾 *{animal_a['emoji']} {name_a}* chosen as parent 1\n\nChoose parent 2:",
        reply_markup=kb,
        parse_mode="Markdown",
    )
