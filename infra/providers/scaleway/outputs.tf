output "ipv4" {
  description = "Публичный IPv4 VPS"
  value       = scaleway_instance_ip.public.address
}

output "hostname" {
  value = scaleway_instance_server.vpn.name
}
