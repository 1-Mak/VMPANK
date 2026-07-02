terraform {
  required_version = ">= 1.5"
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.40"
    }
  }
}

# Креды из окружения (задаются vpnctl, на диск не пишутся — FR-9):
#   SCW_ACCESS_KEY, SCW_SECRET_KEY, SCW_DEFAULT_PROJECT_ID
provider "scaleway" {
  zone = var.region
}
