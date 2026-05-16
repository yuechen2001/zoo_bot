# 🦁 Zoo Bot

A Telegram bot for couples. Build your own virtual zoo by catching and breeding animals — funded by mood check-ins.

---

## Features

- **Mood check-ins** — bot prompts you every 30 min, earn coins for responding
- **Streak multiplier** — longer streaks = more coins per check-in (up to 3×)
- **Catch system** — roll for random animals by rarity, pay coins to attempt
- **Breeding** — pair two animals and wait for an offspring
- **Hunger & happiness** — animals decay over time, feed them to keep them healthy
- **Achievements** — 14 milestones across catching, breeding, and streaks
- **Daily & trivia** — extra ways to earn coins
- **Gamble & slots** — risk your coins for more
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
2. Both send `/start` — each person gets a random starter animal
3. Respond to mood prompts to earn coins
4. Use `/catch` to grow your zoo

---

## Commands

| Command | Description |
|---|---|
| `/start` | Join and receive a starter animal |
| `/zoo` | View your zoo |
| `/catch` | Search for a wild animal |
| `/feed <number>` | Feed animal(s) — 10 🪙 each |
| `/breed <a> <b>` | Breed two animals together |
| `/breed collect` | Claim your finished offspring |
| `/name <number> <name>` | Give an animal a nickname |
| `/achievements` | View your achievements |
| `/daily` | Claim +50 coins once per day |
| `/trivia` | Animal trivia — +40 correct, +5 wrong, 4h cooldown |
| `/gamble <amount>` | Coin flip bet (max 100 🪙) |
| `/slots` | Spin the slot machine (10 🪙 per spin) |
| `/moodstart` | Opt in to mood prompts |
| `/moodstop` | Opt out (resets streak) |
| `/pause <duration>` | Freeze streak — e.g. `/pause 8h` or `/pause 30m` |
| `/resume` | End pause early |
| `/help` | Show all commands |

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

| Rarity | Encounter | Catch rate | Cost |
|---|---|---|---|
| Common ⬜ | 60% | 90% | 20 🪙 |
| Rare 🟦 | 25% | 60% | 60 🪙 |
| Epic 🟪 | 12% | 35% | 80 🪙 |
| Legendary 🟨 | 3% | 10% | 200 🪙 |

Skipping a catch costs half the attempt price. Failed catches lose the full cost — no refund.

---

## Breeding

| Pair | Time | Cost |
|---|---|---|
| Common × Common | 6h | 50 🪙 |
| Common × Rare | 12h | 120 🪙 |
| Rare × Rare | 18h | 200 🪙 |
| Common/Rare × Epic | 28h | 350 🪙 |
| Epic × Epic | 36h | 500 🪙 |
| Any × Legendary | 48h | 800 🪙 |

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
