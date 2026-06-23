# Operations

Zoo Bot runs across three services: a Telegram bot + REST API on a GCP e2-micro VM, and a Phaser.js webapp on Cloudflare Pages. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full layer diagram and rules.

---

## What is automated vs manual

| Action | How it happens |
|---|---|
| Deploy bot + API to VM | Push to `main` → GitHub Actions `deploy` job |
| Deploy webapp to Cloudflare Pages | Push to `main` → Cloudflare Pages auto-build |
| DB migrations | Deploy script runs `migrate.py up` before restarting services |
| Hunger ticks / mood prompts / wild events | Scheduler jobs inside the bot process |
| First-time GCP VM provisioning | `scripts/setup.sh` (runs Terraform) |
| **Sync VM IP to GitHub + Cloudflare after VM change** | **`scripts/post-apply.sh`** (manual — run after `terraform apply`) |
| Create GCP project + enable billing | Manual (browser) |
| BotFather: create bot, get token | Manual (Telegram) |
| Create Cloudflare Pages project + connect GitHub | Manual (Cloudflare dashboard) |
| Generate Cloudflare API token | Manual (Cloudflare dashboard) |

---

## First-time setup

### Prerequisites
- `terraform` — install via `brew install terraform`
- `gcloud` — install via Google Cloud SDK
- `gh` — GitHub CLI, `brew install gh && gh auth login`
- `openssl` — pre-installed on macOS/Linux

### Step-by-step

**1. Manual steps first (browser required)**

| Step | Where |
|---|---|
| Create GCP project, enable billing | [console.cloud.google.com](https://console.cloud.google.com) |
| Enable Compute Engine API | GCP console → APIs & Services |
| Create bot via BotFather, copy token | Telegram → @BotFather |
| Create Cloudflare Pages project: Root = `zoo_webapp`, Framework = Vite | [dash.cloudflare.com](https://dash.cloudflare.com) → Pages → Connect to Git |
| Create Cloudflare API token with "Cloudflare Pages:Edit" permission | `dash.cloudflare.com/profile/api-tokens` → Create Token |
| Note your Cloudflare Account ID from the dashboard URL | `dash.cloudflare.com/{account_id}/pages` |

**2. Run the setup script**

```bash
bash scripts/setup.sh
```

This generates an SSH keypair, creates `zoo_cli/terraform/terraform.tfvars`, runs `terraform apply`, and sets all GitHub secrets. Optionally configures Cloudflare Pages env vars via API.

**3. After Pages first build completes**

Copy the Pages URL (e.g. `https://zoo-bot.pages.dev`) and update `webapp_url` in `zoo_cli/terraform/terraform.tfvars`, then run:

```bash
cd zoo_cli/terraform && terraform apply
```

This writes `WEBAPP_URL` into the VM's `.env` so the bot sends correct `/play` links.

---

## VM recreation runbook

If the VM is destroyed and recreated (e.g. `terraform destroy && terraform apply`):

1. **Run Terraform:**
   ```bash
   cd zoo_cli/terraform && terraform apply
   ```
   The startup script clones the repo, installs deps, creates systemd services, and starts everything automatically.

2. **Sync the new IP** (even with a static IP, always verify):
   ```bash
   GITHUB_REPO=yuechen2001/zoo_bot \
   CF_ACCOUNT_ID=e256b45d12ca4ec6297099043f2dfc95 \
   CF_API_TOKEN=<your-token> \
   CF_PAGES_PROJECT=zoo-bot \
   bash scripts/post-apply.sh
   ```

3. **If the startup script failed** (bot/API not running after a few minutes):
   ```bash
   ssh ubuntu@$(cd zoo_cli/terraform && terraform output -raw vm_external_ip)
   sudo journalctl -u zoobot -n 50
   sudo journalctl -u zooapi -n 50
   # Fix the issue, then:
   sudo systemctl restart zoobot zooapi
   ```

---

## Day-to-day ops

**SSH into the VM:**
```bash
ssh ubuntu@34.74.45.13
# or
ssh -i ~/.ssh/zoo-bot-gcp ubuntu@34.74.45.13
```

**View live logs:**
```bash
ssh ubuntu@34.74.45.13 "sudo journalctl -u zoobot -f"
ssh ubuntu@34.74.45.13 "sudo journalctl -u zooapi -f"
# File-based log (bot only):
ssh ubuntu@34.74.45.13 "tail -f /opt/zoo_bot/zoo_bot.log"
```

**Manual database backup:**
```bash
ssh ubuntu@34.74.45.13 "cp /opt/zoo_bot/zoo_bot.db /opt/zoo_bot/zoo_bot.db.bak.$(date +%Y%m%d)"
```

**Force Cloudflare Pages redeploy** (if auto-deploy disconnected):
```bash
CF_ACCOUNT_ID=e256b45d12ca4ec6297099043f2dfc95 \
CF_API_TOKEN=<your-token> \
CF_PAGES_PROJECT=zoo-bot \
curl -sf -X POST \
  "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/pages/projects/${CF_PAGES_PROJECT}/deployments" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" | python3 -c "import sys,json; d=json.load(sys.stdin); print('triggered' if d['success'] else d['errors'])"
```

---

## Secrets reference

| Secret | Value | Where set | Who uses it |
|---|---|---|---|
| `GCP_VM_IP` | `34.74.45.13` (static) | GitHub repo → Settings → Secrets | GitHub Actions deploy job (SSH host) |
| `SSH_PRIVATE_KEY` | Contents of `~/.ssh/zoo-bot-gcp` | GitHub repo → Settings → Secrets | GitHub Actions deploy job (SSH key) |
| `BOT_TOKEN` / `BOT_TOKEN_PROD` | From BotFather | VM: `/opt/zoo_bot/zoo_cli/.env` | `zoo_cli` bot process |
| `VM_IP` | `34.74.45.13` | Cloudflare Pages → Settings → Env vars | Pages Function (`functions/api/[[path]].js`) proxies to `{ip}.nip.io:8080` |
| `API_SECRET` | `openssl rand -hex 32` | Cloudflare Pages → Settings → Env vars | Pages Function validates incoming requests |
| `CF_API_TOKEN` | Cloudflare scoped token | Local only (never committed) | `scripts/post-apply.sh` to update Pages env vars |

---

## Related docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layer rules, DB patterns, callback routing
- [docs/CONVENTIONS.md](docs/CONVENTIONS.md) — handler structure, coin ops, feature checklists
- [docs/DB_SCHEMA.md](docs/DB_SCHEMA.md) — full table and column reference
- [docs/QUALITY_SCORE.md](docs/QUALITY_SCORE.md) — health grades per area
- [docs/tech-debt.md](docs/tech-debt.md) — known rough edges
