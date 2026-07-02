terraform {
  required_version = ">= 1.5"
  required_providers {
    upcloud = {
      source  = "UpCloudLtd/upcloud"
      version = "~> 5.0"
    }
  }
}

# Креды берутся из окружения: UPCLOUD_USERNAME / UPCLOUD_PASSWORD (задаются vpnctl,
# на диск не пишутся — FR-9).
provider "upcloud" {}
