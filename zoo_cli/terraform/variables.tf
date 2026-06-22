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
  default     = "us-east1-c"
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

variable "webapp_url" {
  description = "Full HTTPS URL of the Cloudflare Pages app (e.g. https://zoo-bot.pages.dev) — passed to the bot as WEBAPP_URL"
  type        = string
  default     = ""
}

variable "api_secret" {
  description = "Shared secret between Cloudflare Pages Function and the API. Generate with: openssl rand -hex 32"
  type        = string
  sensitive   = true
}
