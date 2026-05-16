# 🦁 Zoo Bot

A Telegram bot for couples. Build your own virtual zoo by catching and breeding animals — funded by mood check-ins.

---

## Features

- **Mood check-ins** — bot prompts every 30 min, earn coins for responding
- **Streak multiplier** — longer streaks = more coins per check-in (up to 3×)
- **Catch system** — roll for random animals by rarity, pay coins to attempt
- **Habitat enclosures** — 6 typed enclosures (Woodland, Savanna, Tropical, Aquatic, Tundra, Mythic); upgrade for higher capacity, passive income, and breeding bonuses
- **Breeding** — pair two animals and wait for an offspring; same-habitat pairs get a time reduction
- **Hunger** — animals decay over time, feed them before they run away
- **Achievements** — 14 milestones across catching, breeding, and streaks
- **Daily & trivia** — extra ways to earn coins
- **Gamble & slots** — risk your coins for more
- **Trading** — swap animals with your partner
- **Investments** — park coins for a 25% return after 24h
- **Auto-feed** — set a hunger threshold and coin cap; the bot feeds your animals automatically each tick
- **Animal directory** — browse all 40 species and track which you've discovered
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
4. Use `/catch` to grow your zoo, `/enclosures` to expand capacity

---

## Commands

| Command | Description |
|---|---|
| `/start` | Join and receive a starter animal |
| `/zoo` | View your zoo, one habitat per page — tap ◀ ▶ to browse |
| `/autofeed <threshold> <max_coins>` | Auto-feed animals below hunger threshold each tick (e.g. `/autofeed 50 100`) |
| `/autofeed off` | Disable auto-feed |
| `/directory` | Browse all species and see which you own |
| `/catch` | Search for a wild animal |
| `/feed <numbers>` | Feed animal(s) — 10 🪙 each |
| `/breed <a> <b>` | Breed two animals together |
| `/breed collect` | Claim your finished offspring |
| `/breed status` | Check time remaining on active breed |
| `/name <number> <name>` | Give an animal a nickname |
| `/sell <number>` | Sell an animal for coins |
| `/trade @user <yours> <theirs>` | Offer an animal swap |
| `/enclosures` | View and upgrade your habitat enclosures |
| `/achievements` | View your achievements |
| `/daily` | Claim +50 coins once per day |
| `/trivia` | Animal trivia — +40 correct, +5 wrong, 4h cooldown |
| `/gamble <amount>` | Coin flip bet (max 100 🪙) |
| `/slots` | Spin the slot machine (10 🪙 per spin) |
| `/invest <amount>` | Invest coins (25% return after 24h) |
| `/moodstart` | Opt in to mood prompts |
| `/moodstop` | Opt out (resets streak) |
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

---

## Animals

40 species across 4 rarities:

| Rarity | Encounter | Catch rate | Catch cost |
|---|---|---|---|
| Common ⬜ | 60% | 90% | 20 🪙 |
| Rare 🟦 | 25% | 60% | 60 🪙 |
| Epic 🟪 | 12% | 35% | 80 🪙 |
| Legendary 🟨 | 3% | 10% | 200 🪙 |

Each search costs 10 🪙 upfront. Failed catches lose the attempt cost — no refund.

---

## Enclosures

Every player starts with a level-1 enclosure in all 6 habitats. Upgrade with `/enclosures`.

| Habitat | Animals |
|---|---|
| 🌲 Woodland | Mouse, Snail, Bunny, Fox, Owl, Deer, Hedgehog, Raccoon, Bear, Ladybug |
| 🌾 Savanna | Hamster, Sheep, Chicken, Pig, Cat, Dog, Lion, Giraffe, Elephant |
| 🌴 Tropical | Frog, Parrot, Panda, Koala, Tiger, Gorilla, Peacock |
| 🐠 Aquatic | Duck, Fish, Hippo, Crocodile, Flamingo, Whale, Shark |
| ❄️ Tundra | Penguin, Wolf, Eagle, Mammoth |
| ✨ Mythic | Unicorn, Dragon, T-Rex |

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
| 🎯 First Catch | Catch your first animal |
| 🦁 Zoo Opening | Own 5 animals |
| 🌟 Zoo Master | Own 10 animals |
| 🟦 Rare Find | Catch a rare |
| 🟪 Epic Discovery | Catch an epic |
| 🟨 Legend Hunter | Catch a legendary |
| 🥚 Parent | Collect your first offspring |
| 🐣 Breeder | Collect 5 offspring |
| ✨ Legendary Lineage | Breed a legendary |

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
