# Single VPS with a reserved public IP. SSH key injected via cloud-init so the
# module is self-contained. Terraform state gives idempotency (NFR-1);
# `terraform destroy` supports IP rotation (FR-1.5).

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
