# Единый выход, который читает vpnctl (provision.terraform_apply читает `ipv4`).
output "ipv4" {
  description = "Публичный IPv4 VPS"
  value       = upcloud_server.vpn.network_interface[0].ip_address
}

output "hostname" {
  value = upcloud_server.vpn.hostname
}
