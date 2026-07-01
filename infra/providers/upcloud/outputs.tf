# Uniform output consumed by vpnctl (provision.terraform_apply reads `ipv4`).
output "ipv4" {
  description = "Public IPv4 of the VPS"
  value       = upcloud_server.vpn.network_interface[0].ip_address
}

output "hostname" {
  value = upcloud_server.vpn.hostname
}
