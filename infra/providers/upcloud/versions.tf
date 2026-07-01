terraform {
  required_version = ">= 1.5"
  required_providers {
    upcloud = {
      source  = "UpCloudLtd/upcloud"
      version = "~> 5.0"
    }
  }
}

# Credentials come from env: UPCLOUD_USERNAME / UPCLOUD_PASSWORD (set by vpnctl,
# never written to disk — FR-9).
provider "upcloud" {}
