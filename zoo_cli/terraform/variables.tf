variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region — use us-central1, us-west1, or us-east1 for free tier"
  type        = string
  default     = "us-east1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-east1-b"
}

variable "ssh_user" {
  description = "SSH username for the VM"
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key" {
  description = "SSH public key content (paste the contents of ~/.ssh/id_rsa.pub)"
  type        = string
}

variable "bot_token" {
  description = "Telegram bot token from BotFather"
  type        = string
  sensitive   = true
}

variable "admin_ids" {
  description = "Comma-separated Telegram user IDs allowed to use /admin commands"
  type        = string
}

variable "repo_url" {
  description = "GitHub repo clone URL. For private repos use https://TOKEN@github.com/yuechen2001/zoo_bot.git"
  type        = string
  default     = "https://github.com/yuechen2001/zoo_bot.git"
}

variable "database_path" {
  description = "Path to the SQLite database file on the VM"
  type        = string
  default     = "/opt/zoo_bot/zoo_bot.db"
}

variable "prompt_interval_minutes" {
  description = "How often (in minutes) mood prompts are sent"
  type        = number
  default     = 30
}

variable "timezone" {
  description = "Timezone for the bot"
  type        = string
  default     = "Asia/Singapore"
}

variable "checkin_window_minutes" {
  description = "Minutes users have to respond to a mood prompt"
  type        = number
  default     = 15
}

variable "catch_expiry_minutes" {
  description = "Minutes a catch offer stays open"
  type        = number
  default     = 5
}

variable "webapp_domain" {
  description = "Domain for the Mini App (e.g. zoo.yourdomain.com). Add a CNAME in Cloudflare pointing to <tunnel-id>.cfargotunnel.com."
  type        = string
}

variable "webapp_url" {
  description = "Full HTTPS URL of the Mini App — passed to the bot as WEBAPP_URL (e.g. https://zoo.yourdomain.com)"
  type        = string
}

variable "cloudflare_tunnel_id" {
  description = "UUID of the Cloudflare Tunnel (from: cloudflared tunnel create zoo)"
  type        = string
}

variable "cloudflare_tunnel_credentials" {
  description = "JSON content of the tunnel credentials file (~/.cloudflared/<tunnel-id>.json)"
  type        = string
  sensitive   = true
}
