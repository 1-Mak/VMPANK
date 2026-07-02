# Один VPS с публичным IPv4, SSH-ключом root, минимальным footprint (FR-1.1/1.3).
# Идемпотентность за счёт стейта Terraform (NFR-1); `terraform destroy` сносит всё
# для ротации IP (FR-1.5).

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

  # Держим машину воспроизводимой; реальная настройка делается Ansible'ом после.
  metadata = true
}
