#!/usr/bin/env bash
# Run after any `terraform apply` to sync the VM IP to GitHub and Cloudflare Pages.
# Requires: GITHUB_REPO, CF_ACCOUNT_ID, CF_API_TOKEN, CF_PAGES_PROJECT env vars.
#
# Usage:
#   GITHUB_REPO=yuechen2001/zoo_bot \
#   CF_ACCOUNT_ID=e256b45d12ca4ec6297099043f2dfc95 \
#   CF_API_TOKEN=<token> \
#   CF_PAGES_PROJECT=zoo-bot \
#   bash scripts/post-apply.sh
set -euo pipefail

TF_DIR="$(cd "$(dirname "$0")/../zoo_cli/terraform" && pwd)"

: "${GITHUB_REPO:?GITHUB_REPO env var is required (e.g. yuechen2001/zoo_bot)}"
: "${CF_ACCOUNT_ID:?CF_ACCOUNT_ID env var is required}"
: "${CF_API_TOKEN:?CF_API_TOKEN env var is required}"
: "${CF_PAGES_PROJECT:?CF_PAGES_PROJECT env var is required}"

VM_IP="$(terraform -chdir="$TF_DIR" output -raw vm_external_ip)"
echo "VM IP: $VM_IP"

# ── GitHub secret ─────────────────────────────────────────────────────────────
gh secret set GCP_VM_IP --repo "$GITHUB_REPO" --body "$VM_IP"
echo "✓ GitHub: GCP_VM_IP = $VM_IP"

# ── Cloudflare Pages: update VM_IP env var ────────────────────────────────────
curl -sf -X PATCH \
  "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/pages/projects/${CF_PAGES_PROJECT}" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"deployment_configs\":{\"production\":{\"env_vars\":{\"VM_IP\":{\"value\":\"${VM_IP}\"}}}}}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('✓ Cloudflare Pages: VM_IP updated') if d['success'] else (print('✗ Cloudflare API error:', d['errors']), sys.exit(1))"

# ── Cloudflare Pages: trigger redeploy so new env var is live immediately ─────
curl -sf -X POST \
  "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/pages/projects/${CF_PAGES_PROJECT}/deployments" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('✓ Cloudflare Pages: redeploy triggered (id=' + (d.get('result') or {}).get('id','?') + ')') if d['success'] else (print('✗ Redeploy error:', d['errors']), sys.exit(1))"
