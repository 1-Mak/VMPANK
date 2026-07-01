# Single VPS with a public IPv4, root SSH key, minimal footprint (FR-1.1/1.3).
# Idempotent by virtue of Terraform state (NFR-1); `terraform destroy` removes
# everything for IP rotation (FR-1.5).

resource "upcloud_server" "vpn" {
  hostname = var.hostname
  zone     = var.region
  plan     = var.plan

  template {
    storage = var.image
    size    = 25
  }

  network_interface {
    type = "public"
  }

  login {
    user            = "root"
    keys            = [var.ssh_public_key]
    create_password = false
  }

  # Keep the box reproducible; real config is done by Ansible afterwards.
  metadata = true
}
