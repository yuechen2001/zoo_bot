import db

ARCS = {
    1: "The Zoo Opens",
    2: "The Expedition Prep",
    3: "The Expedition",
    4: "The Legacy",
    5: "The Phenomenon",
    6: "The Ancient Order",
    7: "The Infinite Zoo",
}

# Re-export so handlers can import from one place
__all__ = ["ARCS", "CHAPTERS", "check_quest_advance"]


async def check_quest_advance(user_id: int, ctx) -> None:
    try:
        await _do_check_quest_advance(user_id, ctx)
    except Exception:
        return


async def _do_check_quest_advance(user_id: int, ctx) -> None:
    user = db.get_user(user_id)
    if not user:
        return

    if not db.get_quest_progress(user_id):
        db.start_chapter(user_id, 1)

    while True:
        active_ch = db.get_active_chapter(user_id)
        if active_ch is None:
            break

        ch = CHAPTERS.get(active_ch)
        if not ch:
            break

        user = db.get_user(user_id)
        tasks_passing = sum(1 for t in ch["tasks"] if t["check"](user_id, user))
        tasks_skipped = db.get_quest_tasks_skipped(user_id, active_ch)
        db.set_quest_step(user_id, active_ch, tasks_passing)

        if tasks_passing + tasks_skipped < len(ch["tasks"]):
            break

        db.complete_chapter(user_id, active_ch, ch["reward_coins"])

        if ch["reward_species"]:
            db.award_quest_animal(user_id, ch["reward_species"])

        if ch["reward_title"]:
            db.record_purchase(user_id, ch["reward_title"])

        next_ch = active_ch + 1
        if next_ch in CHAPTERS:
            db.start_chapter(user_id, next_ch)

        if user["group_chat_id"]:
            name = user["username"] or "Someone"
            sp_extra = ""
            if ch["reward_species"]:
                sp = db.get_species_by_name(ch["reward_species"])
                if sp:
                    sp_extra = f"\n{sp['emoji']} *{ch['reward_species']}* added to your zoo!"
            try:
                await ctx.bot.send_message(
                    user["group_chat_id"],
                    f"📖 *{name}* completed *Chapter {active_ch}: {ch['title']}*!\n"
                    f"_{ch['outro']}_\n\n"
                    f"+{ch['reward_coins']}🪙{sp_extra}",
                    parse_mode="Markdown",
                )
            except Exception:
                pass


# ── Chapter definitions ───────────────────────────────────────────────────────

CHAPTERS: dict[int, dict] = {
    # ── Arc 1: The Zoo Opens ──────────────────────────────────────────────────
    1: {
        "arc": 1,
        "title": "First Steps",
        "intro": (
            "The gates are open. A small crowd gathers outside. "
            "Your zoo is officially in business — now fill it."
        ),
        "outro": "The animals are settling in. Word is spreading.",
        "tasks": [
            {
                "desc": "Own 5 animals",
                "check": lambda uid, _: db.count_animals(uid) >= 5,
            },
            {
                "desc": "Feed any animal",
                "check": lambda uid, _: db.get_user(uid)["feeds_given"] >= 1,
            },
            {
                "desc": "Check in at least once",
                "check": lambda uid, _: db.count_mood_checkins(uid) >= 1,
            },
        ],
        "reward_coins": 150,
        "reward_species": None,
        "reward_title": None,
    },
    2: {
        "arc": 1,
        "title": "Building Grounds",
        "intro": (
            "A local conservation fund has noticed your zoo. "
            "They want to see proper infrastructure before any endorsement."
        ),
        "outro": "The construction crew packs up. Your zoo is starting to look professional.",
        "tasks": [
            {
                "desc": "Upgrade any enclosure to level 2+",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 2,
            },
            {
                "desc": "Breed any two animals",
                "check": lambda uid, _: db.count_collected_breeds(uid) >= 1,
            },
        ],
        "reward_coins": 200,
        "reward_species": None,
        "reward_title": None,
    },
    3: {
        "arc": 1,
        "title": "The First Report",
        "intro": (
            "Dr. Chen from the conservation fund has arrived for her inspection. "
            "She is thorough, precise, and hard to impress."
        ),
        "outro": (
            "Dr. Chen stamps her clipboard. 'Adequate. Perhaps more than adequate.' "
            "She slides a crate across the floor — inside, a sleepy Capybara blinks up at you."
        ),
        "tasks": [
            {
                "desc": "Own at least 1 rare animal",
                "check": lambda uid, _: db.user_owns_rarity(uid, "rare"),
            },
            {
                "desc": "Answer a trivia question",
                "check": lambda uid, _: db.count_trivia_answered(uid) >= 1,
            },
            {
                "desc": "Have an enclosure at level 2+ (income enabled)",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 2,
            },
        ],
        "reward_coins": 250,
        "reward_species": "Capybara",
        "reward_title": None,
    },
    # ── Arc 2: The Expedition Prep ────────────────────────────────────────────
    4: {
        "arc": 2,
        "title": "Into the Wild",
        "intro": (
            "Dr. Chen returns with a proposal: a research expedition into the uncharted highlands. "
            "You'll need to prove your catching skills first."
        ),
        "outro": "You bag a haul. Dr. Chen nods. 'You know how to work a field.'",
        "tasks": [
            {
                "desc": "Own 10 animals",
                "check": lambda uid, _: db.count_animals(uid) >= 10,
            },
            {
                "desc": "Own a lure in your inventory",
                "check": lambda uid, _: db.has_any_lure(uid),
            },
        ],
        "reward_coins": 300,
        "reward_species": None,
        "reward_title": None,
    },
    5: {
        "arc": 2,
        "title": "Supply Run",
        "intro": (
            "Every expedition needs funding and supplies. "
            "The fund will match what you put in — but you have to put in first."
        ),
        "outro": "Crates of supplies line the depot. The expedition is taking shape.",
        "tasks": [
            {
                "desc": "Make a purchase from the store",
                "check": lambda uid, _: db.has_any_store_item(uid),
            },
            {
                "desc": "Make an investment",
                "check": lambda uid, _: db.has_any_investment(uid),
            },
        ],
        "reward_coins": 300,
        "reward_species": None,
        "reward_title": None,
    },
    6: {
        "arc": 2,
        "title": "The Departure",
        "intro": (
            "The convoy is ready. Dr. Chen studies your current collection one last time. "
            "'A zoo with range,' she says. 'Good. We're heading into diverse territory.'"
        ),
        "outro": (
            "The trucks roll out at dawn. In a separate cage on the last vehicle, "
            "a Red Panda peers at you with curious amber eyes."
        ),
        "tasks": [
            {
                "desc": "Own at least 1 epic animal",
                "check": lambda uid, _: db.user_owns_rarity(uid, "epic"),
            },
            {
                "desc": "Have animals in 4 different habitats",
                "check": lambda uid, _: db.count_habitats_occupied(uid) >= 4,
            },
        ],
        "reward_coins": 400,
        "reward_species": "Red Panda",
        "reward_title": None,
    },
    # ── Arc 3: The Expedition ─────────────────────────────────────────────────
    7: {
        "arc": 3,
        "title": "Uncharted Territory",
        "intro": (
            "The highlands are unlike anything in the guidebooks. "
            "Strange tracks cross the mud. Something big lives here."
        ),
        "outro": "You set up camp at dusk. Whatever is out there — it's watching.",
        "tasks": [
            {
                "desc": "Own a legendary animal OR collect 10 bred animals",
                "check": lambda uid, _: (
                    db.user_owns_rarity(uid, "legendary") or db.count_collected_breeds(uid) >= 10
                ),
            },
        ],
        "reward_coins": 400,
        "reward_species": None,
        "reward_title": None,
    },
    8: {
        "arc": 3,
        "title": "Strange Sightings",
        "intro": (
            "Nights blur into days. You keep detailed logs — the fund demands it. "
            "The animals here respond to patience, not urgency."
        ),
        "outro": "The data is rich. Dr. Chen calls it 'unprecedented'. You call it exhausting.",
        "tasks": [
            {
                "desc": "Reach a mood streak of 7",
                "check": lambda uid, u: u["streak_windows"] >= 7,
            },
            {
                "desc": "Answer 3 trivia questions total",
                "check": lambda uid, _: db.count_trivia_answered(uid) >= 3,
            },
        ],
        "reward_coins": 450,
        "reward_species": None,
        "reward_title": None,
    },
    9: {
        "arc": 3,
        "title": "The Discovery",
        "intro": (
            "On the last day of the expedition, you find a pool at the base of a waterfall. "
            "Something translucent and alien-looking drifts through the current."
        ),
        "outro": (
            "You carry the specimen back in a sealed tank. "
            "Dr. Chen stares for a long moment. 'That,' she says quietly, 'is an Axolotl.'"
        ),
        "tasks": [
            {
                "desc": "Own 15 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 15,
            },
            {
                "desc": "Have an enclosure at level 3+",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 3,
            },
        ],
        "reward_coins": 600,
        "reward_species": "Axolotl",
        "reward_title": None,
    },
    # ── Arc 4: The Legacy ─────────────────────────────────────────────────────
    10: {
        "arc": 4,
        "title": "Recognition",
        "intro": (
            "The expedition results are published. Headlines follow. "
            "Suddenly everyone knows your zoo's name."
        ),
        "outro": "Fan mail arrives. A documentary crew books a visit. Things are changing.",
        "tasks": [
            {
                "desc": "Reach a mood streak of 14",
                "check": lambda uid, u: u["streak_windows"] >= 14,
            },
            {
                "desc": "Have animals in all 7 habitats",
                "check": lambda uid, _: db.count_habitats_occupied(uid) >= 7,
            },
        ],
        "reward_coins": 600,
        "reward_species": None,
        "reward_title": None,
    },
    11: {
        "arc": 4,
        "title": "The Final Exhibit",
        "intro": (
            "Dr. Chen proposes a permanent exhibit — a living showcase of everything discovered. "
            "It will take your best animals and your best work."
        ),
        "outro": (
            "The exhibit opens on a rainy Tuesday. By Thursday, there's a queue around the block."
        ),
        "tasks": [
            {
                "desc": "Breed a legendary animal",
                "check": lambda uid, _: db.user_bred_rarity(uid, "legendary"),
            },
            {
                "desc": "Own 25 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 25,
            },
        ],
        "reward_coins": 750,
        "reward_species": None,
        "reward_title": None,
    },
    12: {
        "arc": 4,
        "title": "Zoo Legend",
        "intro": (
            "A letter arrives from the International Conservation Board. "
            "They want to name something after your zoo. "
            "Deep in the cloud forests, a bird no one has documented waits."
        ),
        "outro": (
            "The Quetzal lands on your outstretched arm. "
            "Dr. Chen takes the photo. It ends up on the cover of three magazines. "
            "You are, officially, a Zoo Legend."
        ),
        "tasks": [
            {
                "desc": "Have an enclosure at level 5+",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 5,
            },
            {
                "desc": "Own 30 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 30,
            },
        ],
        "reward_coins": 1000,
        "reward_species": "Quetzal",
        "reward_title": "title_expedition",
    },
    # ── Arc 5: The Phenomenon ─────────────────────────────────────────────────
    13: {
        "arc": 5,
        "title": "The Correspondent",
        "intro": (
            "A wildlife journalist has arrived at the gates. "
            "Word of your legendary zoo has spread globally and she wants the full story for her documentary."
        ),
        "outro": (
            "The article goes viral overnight. "
            "Conservation grants flood in from three continents. "
            "The zoo has never been busier."
        ),
        "tasks": [
            {
                "desc": "Maintain a mood streak of 21 days",
                "check": lambda uid, u: u["streak_windows"] >= 21,
            },
            {
                "desc": "Own 35 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 35,
            },
            {
                "desc": "Have an enclosure at level 6+",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 6,
            },
        ],
        "reward_coins": 1000,
        "reward_species": None,
        "reward_title": None,
    },
    14: {
        "arc": 5,
        "title": "The Summit",
        "intro": (
            "You've been invited to speak at the Global Wildlife Summit. "
            "Show them what a truly world-class zoo looks like."
        ),
        "outro": (
            "Standing ovation. "
            "Three PhD students request internships. "
            "A research grant arrives in the mail."
        ),
        "tasks": [
            {
                "desc": "Own 40 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 40,
            },
            {
                "desc": "Have animals in all 8 habitats",
                "check": lambda uid, _: db.count_habitats_occupied(uid) >= 8,
            },
            {
                "desc": "Collect 5 bred offspring",
                "check": lambda uid, _: db.count_collected_breeds(uid) >= 5,
            },
        ],
        "reward_coins": 1200,
        "reward_species": None,
        "reward_title": None,
    },
    15: {
        "arc": 5,
        "title": "The Rarest Find",
        "intro": (
            "A cryptid report from the Siberian taiga — locals have spotted a ghost-striped cat "
            "no one has documented in a decade. One last expedition."
        ),
        "outro": (
            "The tiger steps from the treeline. "
            "Cameras catch every stripe. "
            "Some discoveries are worth a lifetime."
        ),
        "tasks": [
            {
                "desc": "Own 45 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 45,
            },
            {
                "desc": "Have an enclosure at level 7+",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 7,
            },
            {
                "desc": "Maintain a mood streak of 28 days",
                "check": lambda uid, u: u["streak_windows"] >= 28,
            },
        ],
        "reward_coins": 1500,
        "reward_species": "Amur Tiger",
        "reward_title": None,
    },
    # ── Arc 6: The Ancient Order ──────────────────────────────────────────────
    16: {
        "arc": 6,
        "title": "The Archive",
        "intro": (
            "A sealed crate arrives from a private collection — field notes from a "
            "19th-century conservationist who catalogued 60 species before vanishing."
        ),
        "outro": (
            "The notes are real. The locations check out. "
            "You are not the first person to have done this."
        ),
        "tasks": [
            {
                "desc": "Maintain a mood streak of 35 days",
                "check": lambda uid, u: u["streak_windows"] >= 35,
            },
            {
                "desc": "Own 50 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 50,
            },
            {
                "desc": "Collect 15 bred offspring",
                "check": lambda uid, _: db.count_collected_breeds(uid) >= 15,
            },
        ],
        "reward_coins": 1500,
        "reward_species": None,
        "reward_title": None,
    },
    17: {
        "arc": 6,
        "title": "The Pilgrimage",
        "intro": (
            "The notes describe a site — a highland plateau where ancient species still roam. "
            "The pilgrimage begins."
        ),
        "outro": (
            "The plateau exists. The air tastes different up here. " "Something old is watching."
        ),
        "tasks": [
            {
                "desc": "Own 55 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 55,
            },
            {
                "desc": "Have an enclosure at level 7+",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 7,
            },
            {
                "desc": "Answer 10 trivia questions",
                "check": lambda uid, _: db.count_trivia_answered(uid) >= 10,
            },
        ],
        "reward_coins": 1800,
        "reward_species": None,
        "reward_title": None,
    },
    18: {
        "arc": 6,
        "title": "The Covenant",
        "intro": (
            "At the centre of the plateau, a herd of impossible cattle. "
            "The ancient order's covenant: protect them and they will protect the zoo."
        ),
        "outro": (
            "The Aurochs bow their heads. The covenant is made. "
            "The zoo is now part of something far older than itself."
        ),
        "tasks": [
            {
                "desc": "Own 60 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 60,
            },
            {
                "desc": "Have an enclosure at level 8",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 8,
            },
            {
                "desc": "Maintain a mood streak of 45 days",
                "check": lambda uid, u: u["streak_windows"] >= 45,
            },
        ],
        "reward_coins": 2000,
        "reward_species": "Aurochs",
        "reward_title": None,
    },
    # ── Arc 7: The Infinite Zoo ───────────────────────────────────────────────
    19: {
        "arc": 7,
        "title": "Beyond the Horizon",
        "intro": (
            "The conservation board sends an unusual message — "
            "there are species beyond any catalogue. The horizon keeps moving."
        ),
        "outro": (
            "A new shipment arrives. A creature from no known genus. " "The horizon moved again."
        ),
        "tasks": [
            {
                "desc": "Own 65 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 65,
            },
            {
                "desc": "Maintain a mood streak of 50 days",
                "check": lambda uid, u: u["streak_windows"] >= 50,
            },
            {
                "desc": "Own 80 animals total",
                "check": lambda uid, _: db.count_animals(uid) >= 80,
            },
        ],
        "reward_coins": 2000,
        "reward_species": None,
        "reward_title": None,
    },
    20: {
        "arc": 7,
        "title": "The Timeless Collection",
        "intro": (
            "Museums call. Historians visit. "
            "The question becomes: how do you hold infinity in one place?"
        ),
        "outro": ("You don't hold it. You tend it. " "That's the difference."),
        "tasks": [
            {
                "desc": "Own 70 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 70,
            },
            {
                "desc": "Collect 25 bred offspring",
                "check": lambda uid, _: db.count_collected_breeds(uid) >= 25,
            },
            {
                "desc": "Have an enclosure at level 8",
                "check": lambda uid, _: db.get_max_enclosure_level(uid) >= 8,
            },
        ],
        "reward_coins": 2500,
        "reward_species": None,
        "reward_title": None,
    },
    21: {
        "arc": 7,
        "title": "The Eternal Keeper",
        "intro": (
            "The last report. Somewhere above the mythic enclosure, "
            "a comet-shaped light has been appearing at dusk."
        ),
        "outro": (
            "It lands on your shoulder. Cold and warm at once. "
            "The zoo is complete — and somehow, it's just beginning."
        ),
        "tasks": [
            {
                "desc": "Own 75 distinct species",
                "check": lambda uid, _: db.count_distinct_species(uid) >= 75,
            },
            {
                "desc": "Maintain a mood streak of 60 days",
                "check": lambda uid, u: u["streak_windows"] >= 60,
            },
            {
                "desc": "Own 100 animals total",
                "check": lambda uid, _: db.count_animals(uid) >= 100,
            },
        ],
        "reward_coins": 3000,
        "reward_species": "Comet Spirit",
        "reward_title": "title_eternal",
    },
}
