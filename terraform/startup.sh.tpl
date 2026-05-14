#!/bin/bash
set -euo pipefail
exec > /var/log/zoo_bot_startup.log 2>&1

echo "=== Zoo Bot startup script ==="

# ── System dependencies ───────────────────────────────────────────────────────
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git

# ── Clone repo ────────────────────────────────────────────────────────────────
git clone ${repo_url} /opt/zoo_bot
cd /opt/zoo_bot

# ── Python venv + dependencies ────────────────────────────────────────────────
python3 -m venv venv
/opt/zoo_bot/venv/bin/pip install --upgrade pip
/opt/zoo_bot/venv/bin/pip install -r requirements.txt

# ── Write .env ────────────────────────────────────────────────────────────────
cat > /opt/zoo_bot/.env << 'ENVEOF'
BOT_TOKEN=${bot_token}
DATABASE_PATH=${database_path}
PROMPT_INTERVAL_MINUTES=${prompt_interval}
TIMEZONE=${timezone}
CHECKIN_WINDOW_MINUTES=${checkin_window}
CATCH_EXPIRY_MINUTES=${catch_expiry}
ADMIN_IDS=${admin_ids}
ENVEOF

# ── systemd service ───────────────────────────────────────────────────────────
cat > /etc/systemd/system/zoobot.service << 'SVCEOF'
[Unit]
Description=Zoo Bot
After=network.target

[Service]
WorkingDirectory=/opt/zoo_bot
ExecStart=/opt/zoo_bot/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable zoobot
systemctl start zoobot

echo "=== Done. Bot is running ==="
