output "vm_external_ip" {
  description = "External IP of the zoo-bot VM — use this to SSH in"
  value       = google_compute_instance.zoo_bot.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  description = "Command to SSH into the VM"
  value       = "ssh ${var.ssh_user}@${google_compute_instance.zoo_bot.network_interface[0].access_config[0].nat_ip}"
}
