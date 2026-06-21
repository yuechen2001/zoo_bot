terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "zoo-bot-allow-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["zoo-bot"]

  depends_on = [google_project_service.compute]
}

# Cloudflare Tunnel is outbound so ports 80/443 don't need to be public.
# This rule is optional — only useful for direct VM access during debugging.
resource "google_compute_firewall" "allow_web" {
  name    = "zoo-bot-allow-web"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["zoo-bot"]

  depends_on = [google_project_service.compute]
}

resource "google_compute_instance" "zoo_bot" {
  name         = "zoo-bot"
  machine_type = "e2-micro"
  zone         = var.zone
  tags         = ["zoo-bot"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${var.ssh_public_key}"
  }

  metadata_startup_script = templatefile("${path.module}/startup.sh.tpl", {
    bot_token                     = var.bot_token
    admin_ids                     = var.admin_ids
    repo_url                      = var.repo_url
    database_path                 = var.database_path
    prompt_interval               = var.prompt_interval_minutes
    timezone                      = var.timezone
    checkin_window                = var.checkin_window_minutes
    catch_expiry                  = var.catch_expiry_minutes
    webapp_domain                 = var.webapp_domain
    webapp_url                    = var.webapp_url
    cloudflare_tunnel_id          = var.cloudflare_tunnel_id
    cloudflare_tunnel_credentials = var.cloudflare_tunnel_credentials
  })

  depends_on = [google_project_service.compute]
}
