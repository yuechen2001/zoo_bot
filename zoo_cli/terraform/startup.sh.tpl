#!/bin/bash
set -euo pipefail
exec > /var/log/zoo_bot_startup.log 2>&1

echo "=== Zoo Bot startup script ==="

# ── System dependencies ───────────────────────────────────────────────────────
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

# ── Node.js 20 LTS (for webapp build) ────────────────────────────────────────
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# ── Clone repo ────────────────────────────────────────────────────────────────
git clone ${repo_url} /opt/zoo_bot
cd /opt/zoo_bot

# ── Python venv + dependencies (shared by bot and API) ───────────────────────
python3 -m venv venv
/opt/zoo_bot/venv/bin/pip install --upgrade pip
/opt/zoo_bot/venv/bin/pip install -r zoo_cli/requirements.txt
/opt/zoo_bot/venv/bin/pip install -r zoo_api/requirements.txt

# ── Build webapp ──────────────────────────────────────────────────────────────
cd /opt/zoo_bot/zoo_webapp
npm ci
npm run build
cd /opt/zoo_bot

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
WEBAPP_ORIGIN=https://${webapp_domain}
ZOO_BOT_PATH=/opt/zoo_bot/zoo_cli
APIENVEOF

# ── Run DB migrations ─────────────────────────────────────────────────────────
/opt/zoo_bot/venv/bin/python /opt/zoo_bot/zoo_cli/migrate.py up

# ── nginx config ──────────────────────────────────────────────────────────────
cat > /etc/nginx/sites-available/zoo << 'NGINXEOF'
server {
    listen 80;
    server_name ${webapp_domain};

    # Proxy /api/* to uvicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $$host;
        proxy_set_header X-Real-IP $$remote_addr;
        proxy_set_header X-Forwarded-For $$proxy_add_x_forwarded_for;
        proxy_read_timeout 30s;
    }

    # Serve webapp static files
    location / {
        root /opt/zoo_bot/zoo_webapp/dist;
        try_files $$uri $$uri/ /index.html;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/zoo /etc/nginx/sites-enabled/zoo
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

# ── HTTPS via Let's Encrypt ───────────────────────────────────────────────────
# DNS for ${webapp_domain} must point to this VM's IP before this runs.
# If it fails here (DNS not yet set up), run manually:
#   certbot --nginx -d ${webapp_domain} --non-interactive --agree-tos -m ${certbot_email}
certbot --nginx \
  -d ${webapp_domain} \
  --non-interactive \
  --agree-tos \
  -m ${certbot_email} \
  --redirect \
  || echo "WARNING: certbot failed — point DNS to this VM then run certbot manually"

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
ExecStart=/opt/zoo_bot/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
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

# ── Daily DB backup (2am, keep 3 latest copies) ───────────────────────────────
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

echo "=== Done. Bot + API running, nginx serving Mini App ==="
