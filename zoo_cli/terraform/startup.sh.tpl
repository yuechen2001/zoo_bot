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
/opt/zoo_bot/venv/bin/pip install -r zoo_cli/requirements.txt

# ── Write .env ────────────────────────────────────────────────────────────────
cat > /opt/zoo_bot/zoo_cli/.env << 'ENVEOF'
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
WorkingDirectory=/opt/zoo_bot/zoo_cli
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

# ── Daily backup (2am, keep 3 latest copies) ──────────────────────────────────
cat > /usr/local/bin/zoo_backup.sh << 'BACKUPEOF'
#!/bin/bash
BACKUP_DIR=/opt/zoo_bot/backups
DB=/opt/zoo_bot/zoo_bot.db

mkdir -p "$$BACKUP_DIR"
cp "$$DB" "$$BACKUP_DIR/zoo_bot_$$(date +%Y%m%d_%H%M%S).db"
ls -t "$$BACKUP_DIR"/*.db | tail -n +4 | xargs -r rm
BACKUPEOF

chmod +x /usr/local/bin/zoo_backup.sh
echo "0 2 * * * root /usr/local/bin/zoo_backup.sh" > /etc/cron.d/zoo_backup

echo "=== Done. Bot is running ==="
