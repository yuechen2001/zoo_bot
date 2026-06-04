# 🦁 Zoo Bot

A Telegram bot for couples. Build your own virtual zoo by catching and breeding animals — funded by mood check-ins.

---

## Features

- **Mood check-ins** — bot prompts every 30 min, earn coins for responding
- **Streak multiplier** — longer streaks = more coins per check-in (up to 3×)
- **Catch system** — use /catch to encounter a random animal; pay coins to attempt the catch
- **Lures** — optional habitat-specific powerups (1.5× catch rate, filters by habitat); select one during /catch or catch for free without one
- **Wild events** — rare animals appear in the group chat; first to claim with a matching lure wins
- **Habitat enclosures** — 8 typed enclosures (Woodland, Savanna, Tropical, Aquatic, Tundra, Mythic, Spectral, Desert); upgrade for higher capacity, passive income, and breeding bonuses
- **Breeding** — pair two animals and wait for an offspring; same-habitat pairs get a time reduction; elders cannot breed
- **Animal aging** — animals progress through three life stages: 🐣 Juvenile (0–3 days, −20% income), 🐾 Adult (3–30 days), 👴 Elder (30+ days, +60% income, retired from breeding)
- **Shinies** — 1.5% chance on any catch or breed to produce a ⭐ shiny variant
- **Hunger** — animals decay over time, feed them before they run away
- **Foot massage** — halve hunger decay for 1h (25 🪙, 4h cooldown)
- **Animal escapes** — rare event (every 8–16h): an animal escapes its enclosure; lure it back 🎣 (90%), chase it 🏃 (35%), or let it go 🕊️ (30% refund) within a 2h window
- **Zoo visiting** — /visit @username to browse another player's zoo and feed one animal per 24h (costs feed price, earns +15 🪙 bonus)
- **Group trivia** — trivia questions fire in the group chat every 4h; first correct answer +100 🪙; both players correct = couple bonus +30 each; wrong answer −10 🪙
- **Achievements** — 50+ milestones across catching, breeding, streaks, trading, and more
- **Tiered daily rewards** — claim coins daily; consecutive days unlock higher tiers (50 → 75 → 100 → 150 🪙)
- **Trivia** — answer animal trivia with a wager (10/25/50 🪙); win the wager on correct, lose it on wrong; 15 min cooldown
- **Store** — consumables (lures, feed, boosts, instant hatch, income boost, quest task skip), cosmetic titles
- **Quests** — 21-chapter storyline across 7 arcs; earn exclusive animals and titles; replay completed chapters
- **Gamble & slots** — risk your coins for more
- **Trading** — swap animals with your partner
- **Investments** — park coins for a 25% return after 24h
- **Auto-feed** — set a hunger threshold and coin cap; the bot feeds your animals automatically each tick
- **Animal directory** — browse all 107 species and track which you've discovered
- **Admin commands** — debug tools for the bot owner

---

## Setup

### 1. Create a bot

Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.

### 2. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
BOT_ENV=dev
BOT_TOKEN_DEV=your_dev_token
BOT_TOKEN_PROD=your_prod_token
DATABASE_PATH=zoo_bot.db
PROMPT_INTERVAL_MINUTES=30
CHECKIN_WINDOW_MINUTES=15
CATCH_EXPIRY_MINUTES=5
TIMEZONE=Asia/Singapore
ADMIN_IDS=your_telegram_id
```

### 4. Run

```bash
python main.py
```

---

## Getting started in Telegram

1. Add the bot to a group with your partner
2. Both send `/start` — each person gets a random starter animal and a level-1 enclosure in every habitat
3. Respond to mood prompts to earn coins
4. Buy a lure from `/store`, then use `/catch` to grow your zoo
5. Use `/enclosures` to expand capacity and earn passive income

---

## Commands

| Command | Description |
|---|---|
| `/start` | Join and receive a starter animal |
| `/zoo` | View your zoo, one habitat per page — tap ◀ ▶ to browse |
| `/footmassage` | Halve hunger decay for 1h (25 🪙, 4h cooldown) |
| `/catch` | Pick a lure and search for a wild animal (no lure costs 10 🪙) |
| `/feed <numbers>` | Feed animal(s) — cost varies by rarity |
| `/breed <a> <b>` | Breed two animals together |
| `/breed collect` | Claim your finished offspring |
| `/breed status` | Check time remaining on active breed |
| `/name <number> <name>` | Give an animal a nickname |
| `/sell` | Sell an animal for coins (tap to pick, or `/sell <number>` to jump straight to confirm) |
| `/gift <number> @user` | Give an animal to another player |
| `/trade @user <yours> <theirs>` | Offer an animal swap |
| `/visit @username` | Browse another player's zoo; feed one animal per 24h for a coin bonus |
| `/enclosures` | View and upgrade your habitat enclosures — tap 💰 Collect income to claim passive income |
| `/store` | Browse consumables and cosmetic titles |
| `/inventory` | Your bag — use items and equip titles |
| `/quests` | Track the Zoo Expedition storyline (21 chapters, 7 arcs) |
| `/achievements` | View your achievements |
| `/daily` | Claim daily coins (50→75→100→150 on consecutive days) |
| `/trivia` | Animal trivia — place a wager (10/25/50 🪙), win or lose it based on your answer |
| `/gamble <amount>` | Coin flip bet (max 200 🪙) |
| `/slots` | Spin the slot machine (10 🪙 per spin) |
| `/invest <amount>` | Invest coins (25% return after 24h) — tap *Collect now* when ready |
| `/autofeed <threshold> <max_coins>` | Auto-feed animals below hunger threshold each tick (e.g. `/autofeed 50 100`) |
| `/autofeed off` | Disable auto-feed |
| `/directory` | Browse all species and see which you own |
| `/moodstart` | Opt in to mood prompts |
| `/moodstop` | Opt out (streak preserved) |
| `/help` | Show all commands |
| `/admin help` | List all admin & mod commands (pause, resume, give, reset…) |

---

## Mood check-in coins

| Streak | Multiplier |
|---|---|
| 1–3 windows | 1.0× |
| 4–7 windows | 1.25× |
| 8–15 windows | 1.5× |
| 16–29 windows | 2.0× |
| 30+ windows | 3.0× 🔥 |

Base coins per mood: 😢 10 · 😐 20 · 🙂 35 · 😄 55 · 🤩 80

You have **15 minutes** to respond after a prompt. Missing 2 prompts in a row resets your streak.

If everyone in the group calls `/moodstop`, prompts stop for the group entirely — no special group-pause state is set; the bot simply has no opted-in recipients to ping. Prompts resume as soon as any member calls `/moodstart` again.

---

## Animals

107 species across 4 rarities and 8 habitats:

| Rarity | Encounter | Catch rate | Catch cost |
|---|---|---|---|
| Common ⬜ | 57% | 90% | 20 🪙 |
| Rare 🟦 | 25% | 60% | 60 🪙 |
| Epic 🟪 | 14% | 35% | 80 🪙 |
| Legendary 🟨 | 4% | 10% | 200 🪙 |

Catch rate is multiplied by 1.5× when using a habitat-specific lure. Lures are always consumed on use — even if no species are found.

Any successful catch or breed has a **1.5% chance** to produce a ⭐ shiny variant — cosmetic only, displayed prominently in /zoo.

---

## Animal Aging

Animals progress through life stages based on how long you've owned them:

| Stage | Age | Income | Breeding |
|---|---|---|---|
| 🐣 Juvenile | 0–3 days | −20% income | +25% breed time |
| 🐾 Adult | 3–30 days | baseline | baseline |
| 👴 Elder | 30+ days | +60% income | Cannot breed |

Elders are retired — they can't be paired for breeding, but their high income makes them valuable long-term keepers.

---

## Store

Use `/store` to browse and buy items. Use `/inventory` to activate consumables and equip titles — no need to remember item keys.

**Lures** (optional — select during `/catch` for a habitat bonus):

| Item | Price | Effect |
|---|---|---|
| 🌲 Woodland Lure | 60 🪙 | Woodland habitat, 1.5× catch rate |
| 🌾 Savanna Lure | 60 🪙 | Savanna habitat, 1.5× catch rate |
| 🌴 Tropical Lure | 60 🪙 | Tropical habitat, 1.5× catch rate |
| 🐠 Aquatic Lure | 60 🪙 | Aquatic habitat, 1.5× catch rate |
| ❄️ Tundra Lure | 60 🪙 | Tundra habitat, 1.5× catch rate |
| ✨ Mythic Lure | 150 🪙 | Mythic habitat, 1.5× catch rate, epic or legendary only |
| 👻 Spectral Lure | 150 🪙 | Spectral habitat, 1.5× catch rate |
| 🏜️ Desert Lure | 80 🪙 | Desert habitat, 1.5× catch rate |

**Consumables** (sit in your bag until used):

| Item | Price | Effect |
|---|---|---|
| 🍖 Mega Feed | 30 🪙 | Restore one animal's hunger to 100 |
| ⚡ Breed Boost | 80 🪙 | Cut active breed time by 2h |
| 🚀 Breed Accelerator | 100 🪙 | Halve remaining breed time |
| 🐣 Instant Hatch | 500 🪙 | Complete your active breeding immediately |
| 💰 Income Boost | 250 🪙 | Double enclosure passive income for 4h |
| 📜 Quest Task Skip | 1,500 🪙 | Skip one task in your active chapter (max 1 skip per chapter) |
| 🎯 Lucky Token | 80 🪙 | 2× catch rate on next /catch |
| ✨ Mood Booster | 60 🪙 | Double coins on next mood check-in |
| 🛡️ Streak Shield | 150 🪙 | Absorb one streak-breaking miss |
| 🧲 Rare Magnet | 100 🪙 | Guarantee a rare-or-higher encounter on next /catch |
| 💜 Epic Magnet | 300 🪙 | Guarantee an epic-or-higher encounter on next /catch |
| 🪤 Catch Net | 600 🪙 | Guarantee a legendary encounter and successful catch |

**Cosmetic titles** (shown in `/zoo`):

| Item | Price | How to get |
|---|---|---|
| 🎖 Zookeeper | 200 🪙 | Purchase from /store |
| 🌿 Animal Whisperer | 500 🪙 | Purchase from /store |
| 🔬 The Naturalist | 300 🪙 | Purchase from /store |
| 🏛️ Zoo Director | 750 🪙 | Purchase from /store |
| 👑 Zoo Legend | 1,000 🪙 | Purchase from /store |
| 🗺️ Expedition Leader | Free | Complete Arc 4 of the Zoo Expedition |
| ♾️ Eternal Keeper | Free | Complete all 7 arcs of the Zoo Expedition |

---

## Enclosures

Every player starts with a level-1 enclosure in all 8 habitats. Upgrade with `/enclosures`.

| Habitat | Animals (19) |
|---|---|
| 🌲 Woodland | Aurochs, Badger, Bear, Bee, Bunny, Deer, Dove, Fox, Hedgehog, Ladybug, Moose, Mouse, Owl, Raccoon, Red Panda, Skunk, Snail, Squirrel, Wild Boar |
| 🌾 Savanna | Capybara, Cat, Chicken, Cow, Dog, Donkey, Elephant, Giraffe, Hamster, Horse, Kangaroo, Lion, Pig, Rhino, Sheep, Zebra |
| 🌴 Tropical | Ant, Butterfly, Frog, Gorilla, Koala, Lizard, Panda, Parrot, Peacock, Sloth, Snake, Tiger, Turtle |
| 🐠 Aquatic | Axolotl, Crab, Crocodile, Dolphin, Duck, Fish, Flamingo, Hippo, Jellyfish, Lobster, Octopus, Otter, Pufferfish, Shark, Shrimp, Squid, Swan, Whale |
| ❄️ Tundra | Amur Tiger, Arctic Hare, Eagle, Mammoth, Musk Ox, Penguin, Polar Bear, Seal, Snow Leopard, Wolf |
| ✨ Mythic | Comet Spirit, Dodo, Dragon, Elf, Goblin, Merperson, Pegasus, Phoenix, Quetzal, Sauropod, T-Rex, Troll, Unicorn |
| 👻 Spectral | Bat, Demon, Fairy, Genie, Ghost, Imp, Skeleton King, Vampire, Witch, Zombie |
| 🏜️ Desert | Bactrian Camel, Beetle, Camel, Llama, Roadrunner, Sand Drake, Scorpion, Tarantula |

| Level | Capacity | Coins/hr per animal | Breed bonus | Catch bonus | Upgrade cost |
|---|---|---|---|---|---|
| 1 | 3 | — | — | — | Free |
| 2 | 6 | 3 🪙 | −5% breed time | — | 300 🪙 |
| 3 | 10 | 6 🪙 | −10% breed time | — | 800 🪙 |
| 4 | 15 | 12 🪙 | −18% breed time | — | 2,000 🪙 |
| 5 | 21 | 21 🪙 | −25% breed time | — | 5,000 🪙 |
| 6 | 28 | 35 🪙 | −33% breed time | +5% catch rate | 12,000 🪙 |
| 7 | 36 | 55 🪙 | −40% breed time | +10% catch rate | 30,000 🪙 |
| 8 | 45 | 80 🪙 | −50% breed time | +15% catch rate | 75,000 🪙 |

Breed bonus applies when both parents share the same habitat. Income per animal is also affected by life stage (see Animal Aging above).

---

## Breeding

Times shown at full hunger (100). Low hunger can double the wait.

| Pair | Base time | Cost |
|---|---|---|
| Common × Common | 30m | 50 🪙 |
| Common × Rare | 45m | 120 🪙 |
| Rare × Rare | 1h | 200 🪙 |
| Common × Epic | 1h 15m | 250 🪙 |
| Rare × Epic | 1h 30m | 300 🪙 |
| Epic × Epic | 2h | 400 🪙 |
| Common × Legendary | 1h 15m | 500 🪙 |
| Rare × Legendary | 1h 30m | 600 🪙 |
| Epic × Legendary | 2h | 700 🪙 |
| Legendary × Legendary | 2h | 800 🪙 |

Offspring inherits one parent's rarity, with a **10% chance** of bumping up one tier. Elder animals cannot breed.

---

## Achievements

| Achievement | Condition |
|---|---|
| 👣 First Step | Complete your first mood check-in |
| 🔥 On a Roll | 5-window streak |
| 💫 Dedicated | 10-window streak |
| ⚡ Unstoppable | 25-window streak |
| 👑 Legendary Checker | 50-window streak |
| 💫 Centurion | 100-window streak |
| 🎭 Mood Master | 50 mood check-ins |
| 🎭 Mood Legend | 100 mood check-ins |
| 🎯 First Catch | Catch your first animal |
| 🦁 Zoo Opening | Own 5 animals |
| 🌟 Zoo Master | Own 10 animals |
| 🐘 Full House | Own 20 animals |
| 🏟 Mega Zoo | Own 30 animals |
| 🏟️ Megazoo | Own 50 animals |
| 🟦 Rare Find | Catch your first rare animal |
| 🟪 Epic Discovery | Catch your first epic animal |
| 🟨 Legend Hunter | Catch your first legendary animal |
| ✨ Mythic Tamer | Catch your first mythic animal |
| 👻 Ghost Whisperer | Catch your first Spectral creature |
| 🕸️ Spirit Collector | Own 3 Spectral creatures |
| 💀 Haunted Keeper | Own at least one of every Spectral species |
| 🏜️ Sand Walker | Catch your first Desert animal |
| 🐪 Desert Nomad | Own 3 Desert animals |
| 🐲 Dune Lord | Own at least one of every Desert species |
| 🌈 Collector | Own at least one animal of every rarity |
| 🗺️ Explorer | Own an animal from every habitat |
| 📚 Variety Pack | Own 10 different species |
| 📖 Naturalist | Own 20 different species |
| 🔬 Zoologist | Own 30 different species |
| ⭐ Starborn | Obtain your first shiny animal |
| 🌟 Constellation | Own 3 shiny animals at once |
| 🥚 Parent | Collect your first offspring |
| 🐣 Breeder | Collect 5 offspring |
| 🐥 Prolific | Collect 10 offspring |
| 🧬 Master Breeder | Collect 20 offspring |
| 💜 Epic Lineage | Breed an epic offspring |
| ✨ Legendary Lineage | Breed a legendary offspring |
| 💰 Coin Hoarder | Accumulate 500 coins |
| 💎 Wealthy | Accumulate 1,000 coins |
| 🏦 Tycoon | Accumulate 5,000 coins |
| 🏦 Millionaire | Accumulate 10,000 coins |
| ⚡ Quick Reflexes | Catch your first wild event animal |
| 🤝 Trader | Complete your first animal trade |
| 💸 Merchant | Sell your first animal |
| 🍽 Caretaker | Feed an animal for the first time |
| 🧠 Curious Mind | Answer your first trivia question |
| 📚 Quiz Whiz | Answer 10 trivia questions |
| 🌅 Early Bird | Claim your first daily reward |
| 🛍 Shopkeeper | Buy your first item from the store |
| 🎁 Generous Soul | Give an animal to another player |
| 🏗 Builder | Upgrade an enclosure for the first time |
| 🏰 Renovator | Upgrade any enclosure to level 6 |
| 🗼 Grand Builder | Upgrade any enclosure to level 7 |
| 🏛 Master Architect | Reach max level on any enclosure |

---

## Deployment (GCP)

Terraform config is in `terraform/`. Provisions a free-tier e2-micro VM (us-east1) with a startup script that clones the repo, installs deps, and starts the bot as a systemd service.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# fill in your values
terraform init
terraform apply
```

Pushes to `main` auto-deploy via GitHub Actions (requires `GCP_VM_IP` and `SSH_PRIVATE_KEY` secrets).
