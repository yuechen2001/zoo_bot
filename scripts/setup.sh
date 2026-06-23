#!/usr/bin/env bash
# First-time provisioning for zoo-bot.
# Automates everything except: GCP project creation, BotFather, Cloudflare Pages project setup.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
die()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$REPO_ROOT/zoo_cli/terraform"
SSH_KEY="$HOME/.ssh/zoo-bot-gcp"

echo ""
echo "=== Zoo Bot — First-time setup ==="
echo ""

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
echo "Checking prerequisites..."
for cmd in terraform gcloud gh openssl; do
  command -v "$cmd" &>/dev/null || die "'$cmd' not found. Install it and re-run."
done
ok "All prerequisites found"

# ── 2. SSH keypair ────────────────────────────────────────────────────────────
if [[ -f "$SSH_KEY" ]]; then
  warn "SSH key already exists at $SSH_KEY — reusing it"
else
  ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "zoo-bot-gcp"
  ok "Generated SSH keypair at $SSH_KEY"
fi
SSH_PUB_KEY="$(cat "${SSH_KEY}.pub")"

# ── 3. Generate api_secret ────────────────────────────────────────────────────
API_SECRET="$(openssl rand -hex 32)"
ok "Generated api_secret"

# ── 4. Prompt for human-only values ──────────────────────────────────────────
echo ""
echo "Enter the following values (all are required except Cloudflare which can be skipped):"
echo ""

read -rp "GCP project ID: " GCP_PROJECT_ID
[[ -n "$GCP_PROJECT_ID" ]] || die "GCP project ID is required"

read -rp "Telegram bot token (from BotFather): " BOT_TOKEN
[[ -n "$BOT_TOKEN" ]] || die "Bot token is required"

read -rp "Admin Telegram user ID: " ADMIN_ID
[[ -n "$ADMIN_ID" ]] || die "Admin user ID is required"

read -rp "GitHub repo (e.g. yuechen2001/zoo_bot): " GITHUB_REPO
[[ -n "$GITHUB_REPO" ]] || die "GitHub repo is required"

read -rp "Cloudflare Pages URL (e.g. https://zoo-bot.pages.dev) [leave blank to skip]: " WEBAPP_URL
WEBAPP_URL="${WEBAPP_URL:-}"

read -rp "Cloudflare account ID [leave blank to skip Cloudflare setup]: " CF_ACCOUNT_ID
CF_ACCOUNT_ID="${CF_ACCOUNT_ID:-}"

CF_API_TOKEN=""
CF_PAGES_PROJECT=""
if [[ -n "$CF_ACCOUNT_ID" ]]; then
  read -rp "Cloudflare API token (Pages:Edit permission): " CF_API_TOKEN
  read -rp "Cloudflare Pages project name (e.g. zoo-bot): " CF_PAGES_PROJECT
fi

# ── 5. Write terraform.tfvars ─────────────────────────────────────────────────
echo ""
echo "Writing terraform.tfvars..."
cat > "$TF_DIR/terraform.tfvars" << EOF
project_id     = "$GCP_PROJECT_ID"
region         = "us-east1"
zone           = "us-east1-b"
ssh_user       = "ubuntu"
ssh_public_key = "$SSH_PUB_KEY"

bot_token      = "$BOT_TOKEN"
admin_ids      = "$ADMIN_ID"

repo_url       = "https://github.com/$GITHUB_REPO.git"
webapp_url     = "$WEBAPP_URL"
api_secret     = "$API_SECRET"
EOF
ok "Wrote $TF_DIR/terraform.tfvars"

# ── 6. Terraform init + plan + apply ─────────────────────────────────────────
echo ""
echo "Running terraform init..."
terraform -chdir="$TF_DIR" init

echo ""
echo "Running terraform plan..."
terraform -chdir="$TF_DIR" plan

echo ""
read -rp "Apply this plan? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || die "Aborted."

echo ""
echo "Applying..."
terraform -chdir="$TF_DIR" apply -auto-approve
ok "Terraform apply complete"

# ── 7. Read VM IP ─────────────────────────────────────────────────────────────
VM_IP="$(terraform -chdir="$TF_DIR" output -raw vm_external_ip)"
ok "VM IP: $VM_IP"

# ── 8. Set GitHub secrets ─────────────────────────────────────────────────────
echo ""
echo "Setting GitHub secrets..."
gh secret set GCP_VM_IP     --repo "$GITHUB_REPO" --body "$VM_IP"
ok "GitHub: GCP_VM_IP = $VM_IP"

gh secret set SSH_PRIVATE_KEY --repo "$GITHUB_REPO" --body "$(cat "$SSH_KEY")"
ok "GitHub: SSH_PRIVATE_KEY set"

# ── 9. Optional: Cloudflare Pages env vars ────────────────────────────────────
if [[ -n "$CF_ACCOUNT_ID" && -n "$CF_API_TOKEN" && -n "$CF_PAGES_PROJECT" ]]; then
  echo ""
  echo "Configuring Cloudflare Pages env vars..."

  curl -sf -X PATCH \
    "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/pages/projects/${CF_PAGES_PROJECT}" \
    -H "Authorization: Bearer ${CF_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"deployment_configs\":{\"production\":{\"env_vars\":{\"VM_IP\":{\"value\":\"${VM_IP}\"},\"API_SECRET\":{\"value\":\"${API_SECRET}\"}}}}}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('✓ Cloudflare Pages: VM_IP + API_SECRET set') if d['success'] else (print('✗ Cloudflare API error:', d['errors']), sys.exit(1))"

  echo "Triggering Cloudflare Pages redeploy..."
  curl -sf -X POST \
    "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/pages/projects/${CF_PAGES_PROJECT}/deployments" \
    -H "Authorization: Bearer ${CF_API_TOKEN}" \
    -H "Content-Type: application/json" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('✓ Cloudflare Pages: redeploy triggered') if d['success'] else (print('✗ Redeploy error:', d['errors']), sys.exit(1))"
fi

# ── 10. Print remaining manual steps ─────────────────────────────────────────
echo ""
echo "============================================================"
echo " Setup complete! Remaining manual steps:"
echo "============================================================"
echo ""
if [[ -z "$WEBAPP_URL" ]]; then
  echo " 1. Create Cloudflare Pages project:"
  echo "    → dash.cloudflare.com → Pages → Connect to Git"
  echo "    → Set Root directory = zoo_webapp, Framework = Vite"
  echo "    → After first build, copy the Pages URL (e.g. https://zoo-bot.pages.dev)"
  echo "    → Update webapp_url in $TF_DIR/terraform.tfvars"
  echo "    → Run: cd $TF_DIR && terraform apply"
  echo ""
fi
if [[ -z "$CF_ACCOUNT_ID" ]]; then
  echo " 2. Set Cloudflare Pages env vars manually:"
  echo "    → dash.cloudflare.com → Pages → zoo-bot → Settings → Env vars"
  echo "    → VM_IP = $VM_IP"
  echo "    → API_SECRET = $API_SECRET"
  echo "    (Save API_SECRET somewhere safe — it won't be shown again)"
  echo ""
fi
echo " Push to main → GitHub Actions will CI + deploy automatically."
echo ""
