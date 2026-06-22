#!/bin/bash
set -euo pipefail
exec > /var/log/zoo_bot_startup.log 2>&1

echo "=== Zoo Bot startup script ==="

# ── System dependencies ───────────────────────────────────────────────────────
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl gnupg

# ── Google Cloud CLI (for gsutil DB backup/restore) ───────────────────────────
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | tee /etc/apt/sources.list.d/google-cloud-sdk.list
apt-get update -y
apt-get install -y google-cloud-cli

# ── Clone repo ────────────────────────────────────────────────────────────────
git clone ${repo_url} /opt/zoo_bot
cd /opt/zoo_bot

# ── Python venv + dependencies (shared by bot and API) ───────────────────────
python3 -m venv venv
/opt/zoo_bot/venv/bin/pip install --upgrade pip
/opt/zoo_bot/venv/bin/pip install -r zoo_cli/requirements.txt
/opt/zoo_bot/venv/bin/pip install -r zoo_api/requirements.txt

# ── Restore DB from GCS (no-op on first ever run) ────────────────────────────
echo "${backup_bucket}" > /etc/zoo_backup_bucket
gsutil cp gs://${backup_bucket}/zoo_bot.db ${database_path} 2>/dev/null \
  && echo "DB restored from GCS" \
  || echo "No GCS backup found — starting with empty DB"

# ── Run DB migrations ─────────────────────────────────────────────────────────
/opt/zoo_bot/venv/bin/python /opt/zoo_bot/zoo_cli/migrate.py up

# ── Write bot .env ────────────────────────────────────────────────────────────
cat > /opt/zoo_bot/zoo_cli/.env << 'ENVEOF'
BOT_TOKEN=${bot_token}
DATABASE_PATH=${database_path}
PROMPT_INTERVAL_MINUTES=${prompt_interval}
TIMEZONE=${timezone}
CHECKIN_WINDOW_MINUTES=${checkin_window}
CATCH_EXPIRY_MINUTES=${catch_expiry}
ADMIN_IDS=${admin_ids}
WEBAPP_URL=${webapp_url}
ENVEOF

# ── Write API .env ────────────────────────────────────────────────────────────
cat > /opt/zoo_bot/zoo_api/.env << 'APIENVEOF'
DATABASE_PATH=${database_path}
BOT_TOKEN=${bot_token}
WEBAPP_ORIGIN=*
ZOO_BOT_PATH=/opt/zoo_bot/zoo_cli
API_SECRET=${api_secret}
APIENVEOF

# ── Bot systemd service ───────────────────────────────────────────────────────
cat > /etc/systemd/system/zoobot.service << 'SVCEOF'
[Unit]
Description=Zoo Bot (Telegram CLI)
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

# ── API systemd service ───────────────────────────────────────────────────────
cat > /etc/systemd/system/zooapi.service << 'SVCEOF'
[Unit]
Description=Zoo API (FastAPI)
After=network.target

[Service]
WorkingDirectory=/opt/zoo_bot/zoo_api
ExecStart=/opt/zoo_bot/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable zoobot zooapi
systemctl start zoobot zooapi

# ── Hourly DB backup to GCS + keep 3 local copies ────────────────────────────
cat > /usr/local/bin/zoo_backup.sh << 'BACKUPEOF'
#!/bin/bash
DB=/opt/zoo_bot/zoo_bot.db
BUCKET=$(cat /etc/zoo_backup_bucket)
BACKUP_DIR=/opt/zoo_bot/backups

gsutil cp "$DB" "gs://$BUCKET/zoo_bot.db"

mkdir -p "$BACKUP_DIR"
cp "$DB" "$BACKUP_DIR/zoo_bot_$(date +%Y%m%d_%H%M%S).db"
ls -t "$BACKUP_DIR"/*.db | tail -n +4 | xargs -r rm
BACKUPEOF

chmod +x /usr/local/bin/zoo_backup.sh
echo "0 * * * * root /usr/local/bin/zoo_backup.sh" > /etc/cron.d/zoo_backup

echo "=== Done. Bot + API running. DB backed up hourly to GCS. ==="
