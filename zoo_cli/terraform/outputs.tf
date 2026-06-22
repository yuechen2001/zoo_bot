output "vm_external_ip" {
  description = "Static external IP of the zoo-bot VM"
  value       = google_compute_address.static_ip.address
}

output "ssh_command" {
  description = "Command to SSH into the VM"
  value       = "ssh ${var.ssh_user}@${google_compute_address.static_ip.address}"
}
