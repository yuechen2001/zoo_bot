# 🫧 Mr. Slime

A cute Telegram bot for couples. Take care of a shared slime pet by checking in on your moods — the faster you respond, the more you earn.

---

## Features

- **Mood check-ins** — the bot pings you both every 30 minutes with a vibe prompt
- **Time-based rewards** — respond fast for more coins and XP
- **Shared slime pet** — grows and evolves based on your combined moods
- **Decoration store** — spend coins on hats, eyes, accessories, and backgrounds
- **Streaks** — daily streaks with milestone bonuses
- **Couple bonuses** — extra XP when both of you respond to the same prompt

---

## Setup

### 1. Create a bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram and create a new bot. Copy the token.

### 2. Install dependencies

```bash
cd mr-slime
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
BOT_TOKEN=your_token_here
DATABASE_PATH=mr_slime.db
CHECKIN_INTERVAL_MINUTES=30
TIMEZONE=Asia/Shanghai
```

### 4. Run

```bash
python main.py
```

---

## Getting started in Telegram

1. Both of you open the bot and send `/start`
2. One person shares their **invite code** with the other
3. The other person sends the code (or uses `/join CODE`)
4. Name your slime
5. Wait for the first mood check ping, or use `/checkin` right away

---

## Commands

| Command | Description |
|---|---|
| `/start` | Set up and get your invite code |
| `/join CODE` | Link up with your partner |
| `/checkin` | Log your mood manually |
| `/pet` | See your slime |
| `/status` | Today's vibes for both of you |
| `/store` | Browse and buy decorations |
| `/streak` | Your streak and coin balance |
| `/rename Name` | Rename your slime |
| `/unequip slot` | Remove a decoration (`hat`, `eyes`, `accessory`, `background`) |
| `/help` | Show all commands |

---

## Check-in points

| Response time | Coins | XP |
|---|---|---|
| Within 5 min ⚡ | 15 | 15 |
| Within 10 min ✅ | 10 | 10 |
| Within 15 min 🐢 | 5 | 5 |
| After 15 min 💤 | 0 | 0 |

Pet happiness still updates from your vibe even if you're too slow.

Both responding to the same prompt gives **+10 bonus XP** to your slime.

---

## Pet stages

| XP | Stage |
|---|---|
| 0 | 🫧 Egg |
| 100 | 💚 Baby Slime |
| 300 | 🟢 Teen Slime |
| 600 | 💚 Adult Slime |
| 1000 | 🌟 Legendary Slime |

---

## Store slots

- **Hat** 🎩 — Top Hat, Party Hat, Crown, Flower Crown, Witch Hat, Chef Hat
- **Eyes** 👀 — Sunglasses, Heart Eyes, Star Eyes, Sleepy Eyes, UwU
- **Accessory** 🎀 — Bow, Star, Diamond, Rainbow, Lightning, Mushroom
- **Background** 🖼 — Space, Ocean, Forest, Cherry Blossom, Fire, Snowfall

---

## Streak bonuses

Every **7-day streak** awards **+50 bonus coins**.
