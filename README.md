# 🦁 Zoo Bot

A Telegram bot for couples. Build your own virtual zoo by catching and breeding animals — funded by mood check-ins.

---

## Features

- **Mood check-ins** — bot prompts every 30 min, earn coins for responding
- **Streak multiplier** — longer streaks = more coins per check-in (up to 3×)
- **Catch system** — use /catch to encounter a random animal; pay coins to attempt the catch
- **Lures** — optional habitat-specific powerups (1.5× catch rate, filters by habitat); select one during /catch or catch for free without one
- **Habitat enclosures** — 6 typed enclosures (Woodland, Savanna, Tropical, Aquatic, Tundra, Mythic); upgrade for higher capacity, passive income, and breeding bonuses
- **Breeding** — pair two animals and wait for an offspring; same-habitat pairs get a time reduction
- **Hunger** — animals decay over time, feed them before they run away
- **Foot massage** — halve hunger decay for 1h (25 🪙, 4h cooldown)
- **Achievements** — 14 milestones across catching, breeding, and streaks
- **Tiered daily rewards** — claim coins daily; consecutive days unlock higher tiers (50 → 75 → 100 → 150 🪙)
- **Trivia** — answer animal trivia for bonus coins
- **Store** — consumables (lures, feed, boosts), cosmetic titles
- **Gamble & slots** — risk your coins for more
- **Trading** — swap animals with your partner
- **Investments** — park coins for a 25% return after 24h
- **Auto-feed** — set a hunger threshold and coin cap; the bot feeds your animals automatically each tick
- **Animal directory** — browse all 58 species and track which you've discovered
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
| `/feed <numbers>` | Feed animal(s) — 10 🪙 each |
| `/breed <a> <b>` | Breed two animals together |
| `/breed collect` | Claim your finished offspring |
| `/breed status` | Check time remaining on active breed |
| `/name <number> <name>` | Give an animal a nickname |
| `/sell` | Sell an animal for coins (tap to pick from list) |
| `/gift <number> @user` | Give an animal to another player |
| `/trade @user <yours> <theirs>` | Offer an animal swap |
| `/enclosures` | View and upgrade your habitat enclosures — tap 💰 Collect income to claim passive income |
| `/store` | Browse consumables and cosmetic titles |
| `/inventory` | Your bag — use items and equip titles |
| `/achievements` | View your achievements |
| `/daily` | Claim daily coins (50→75→100→150 on consecutive days) |
| `/trivia` | Animal trivia — +40 correct, +5 wrong, 4h cooldown |
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

58 species across 4 rarities:

| Rarity | Encounter | Catch rate | Catch cost |
|---|---|---|---|
| Common ⬜ | 57% | 90% | 20 🪙 |
| Rare 🟦 | 25% | 60% | 60 🪙 |
| Epic 🟪 | 14% | 35% | 80 🪙 |
| Legendary 🟨 | 4% | 10% | 200 🪙 |

Catch rate is multiplied by 1.5× when using a habitat-specific lure. Lures are always consumed on use — even if no species are found.

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
| 🌟 Mythic Lure | 150 🪙 | Mythic habitat, 1.5× catch rate, epic or legendary only |

**Consumables** (sit in your bag until used):

| Item | Price | Effect |
|---|---|---|
| 🍖 Mega Feed | 30 🪙 | Restore one animal's hunger to 100 |
| ⚡ Breed Boost | 80 🪙 | Cut active breed time by 2h |
| 🚀 Breed Accelerator | 100 🪙 | Halve remaining breed time |
| 🎯 Lucky Token | 80 🪙 | 2× catch rate on next /catch |
| ✨ Mood Booster | 60 🪙 | Double coins on next mood check-in |
| 🪤 Catch Net | 600 🪙 | Guarantee a legendary encounter and successful catch |
| 🧲 Rare Magnet | 100 🪙 | Guarantee a rare-or-higher encounter on next /catch |

**Cosmetic titles** (shown in `/zoo`):

| Item | Price |
|---|---|
| 🎖 Zookeeper | 200 🪙 |
| 🌿 Animal Whisperer | 500 🪙 |
| 👑 Zoo Legend | 1,000 🪙 |

---

## Enclosures

Every player starts with a level-1 enclosure in all 6 habitats. Upgrade with `/enclosures`.

| Habitat | Animals |
|---|---|
| 🌲 Woodland | Mouse, Snail, Squirrel, Ladybug, Bunny, Fox, Owl, Deer, Hedgehog, Raccoon, Badger, Bear |
| 🌾 Savanna | Hamster, Sheep, Chicken, Pig, Cat, Dog, Zebra, Lion, Rhino, Giraffe, Elephant |
| 🌴 Tropical | Frog, Turtle, Lizard, Parrot, Snake, Butterfly, Panda, Koala, Tiger, Gorilla, Peacock |
| 🐠 Aquatic | Duck, Fish, Crab, Pufferfish, Dolphin, Octopus, Squid, Hippo, Crocodile, Flamingo, Whale, Shark |
| ❄️ Tundra | Polar Bear, Arctic Hare, Penguin, Seal, Musk Ox, Wolf, Snow Leopard, Eagle, Mammoth |
| ✨ Mythic | Phoenix, Unicorn, Dragon, T-Rex |

| Level | Capacity | Coins/hr per animal | Breed bonus | Upgrade cost |
|---|---|---|---|---|
| 1 | 3 | — | — | Free |
| 2 | 6 | 1 🪙 | −5% breed time | 300 🪙 |
| 3 | 10 | 2 🪙 | −15% breed time | 800 🪙 |
| 4 | 15 | 4 🪙 | −25% breed time | 2,000 🪙 |
| 5 | 21 | 7 🪙 | −40% breed time | 5,000 🪙 |

Breed bonus applies when both parents share the same habitat.

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

Offspring inherits one parent's rarity, with a **10% chance** of bumping up one tier.

---

## Achievements

| Achievement | Condition |
|---|---|
| 👣 First Step | Complete your first check-in |
| 🔥 On a Roll | 5-window streak |
| 💫 Dedicated | 10-window streak |
| ⚡ Unstoppable | 25-window streak |
| 👑 Legendary Checker | 50-window streak |
| 💫 Centurion | 100-window streak |
| 🎯 First Catch | Catch your first animal |
| 🦁 Zoo Opening | Own 5 animals |
| 🌟 Zoo Master | Own 10 animals |
| 🐘 Full House | Own 20 animals |
| 🏟 Mega Zoo | Own 30 animals |
| 🟦 Rare Find | Catch a rare |
| 🟪 Epic Discovery | Catch an epic |
| 🟨 Legend Hunter | Catch a legendary |
| ✨ Mythic Tamer | Catch a mythic animal |
| 🗺️ Explorer | Own an animal from every habitat |
| 📚 Variety Pack | Own 10 different species |
| 📖 Naturalist | Own 20 different species |
| 🥚 Parent | Collect your first offspring |
| 🐣 Breeder | Collect 5 offspring |
| 🐥 Prolific | Collect 10 offspring |
| 🧬 Master Breeder | Collect 20 offspring |
| 💜 Epic Lineage | Breed an epic offspring |
| ✨ Legendary Lineage | Breed a legendary offspring |
| 🎭 Mood Master | 50 mood check-ins |
| 🎭 Mood Legend | 100 mood check-ins |
| 💰 Coin Hoarder | Accumulate 500 coins |
| 💎 Wealthy | Accumulate 1,000 coins |
| 🏦 Tycoon | Accumulate 5,000 coins |
| 🏦 Millionaire | Accumulate 10,000 coins |

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
