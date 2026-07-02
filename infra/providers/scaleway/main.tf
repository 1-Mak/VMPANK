# Один VPS с зарезервированным публичным IP. SSH-ключ прокидывается через cloud-init,
# чтобы модуль был самодостаточным. Стейт Terraform даёт идемпотентность (NFR-1);
# `terraform destroy` поддерживает ротацию IP (FR-1.5).

resource "scaleway_instance_ip" "public" {}

locals {
  cloud_init = <<-EOT
    #cloud-config
    users:
      - name: root
        ssh_authorized_keys:
          - ${var.ssh_public_key}
    disable_root: false
    ssh_pwauth: false
  EOT
}

resource "scaleway_instance_server" "vpn" {
  name  = var.hostname
  type  = var.plan
  image = var.image
  ip_id = scaleway_instance_ip.public.id
  zone  = var.region

  root_volume {
    size_in_gb = 20
  }

  user_data = {
    cloud-init = local.cloud_init
  }
}
