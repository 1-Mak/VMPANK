output "ipv4" {
  description = "Public IPv4 of the VPS"
  value       = scaleway_instance_ip.public.address
}

output "hostname" {
  value = scaleway_instance_server.vpn.name
}
