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

resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_compute_address" "static_ip" {
  name   = "zoo-bot-external"
  region = var.region

  depends_on = [google_project_service.compute]
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

# Port 8000 is the FastAPI backend. It is protected by X-Internal-API-Key so
# it can be public — only Cloudflare Pages Functions know the secret.
resource "google_compute_firewall" "allow_api" {
  name    = "zoo-bot-allow-api"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["zoo-bot"]

  depends_on = [google_project_service.compute]
}

# GCS bucket for SQLite backups — survives VM recreation
resource "google_storage_bucket" "db_backup" {
  name          = "zoo-bot-db-${var.project_id}"
  location      = "US"
  force_destroy = true

  depends_on = [google_project_service.storage]
}

data "google_compute_default_service_account" "default" {
  depends_on = [google_project_service.compute]
}

resource "google_storage_bucket_iam_member" "vm_db_access" {
  bucket = google_storage_bucket.db_backup.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${data.google_compute_default_service_account.default.email}"
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
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  # Attach default service account so the VM can read/write the GCS backup bucket
  service_account {
    email  = data.google_compute_default_service_account.default.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${var.ssh_public_key}"
  }

  metadata_startup_script = templatefile("${path.module}/startup.sh.tpl", {
    bot_token       = var.bot_token
    admin_ids       = var.admin_ids
    repo_url        = var.repo_url
    database_path   = var.database_path
    prompt_interval = var.prompt_interval_minutes
    timezone        = var.timezone
    checkin_window  = var.checkin_window_minutes
    catch_expiry    = var.catch_expiry_minutes
    webapp_url      = var.webapp_url
    api_secret      = var.api_secret
    backup_bucket   = "zoo-bot-db-${var.project_id}"
  })

  depends_on = [google_project_service.compute]
}
